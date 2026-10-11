# Manufacturing (MFG)

`std::mfg` turns a released design into made parts through one typed plan: Ingot intent, Wasm planning, Anvil geometry and Flux physics. Every toolpath, nest, mold, routing, cost and passport is a deterministic function of the design, checked by oracles. A person approves each program, the machine gateway checks that Approval, and a person at the device starts it.

## Scope, layering and core types

| Area | MFG owns | Others own |
| --- | --- | --- |
| Process planning | Setups, workingsteps, toolpaths, posts, nests, builds, routings, setup sheets | None |
| Process physics | Process setups, boundary conditions, process data, checks | Flux (forms, solvers); COV (models, envelopes) |
| Design checks | Process DFM, DFA and DfAM checks against process profiles | MEC (design checks); ELX (board DRC) |
| Product structure | Routings, program Items, as-built records | KLN and `repo` (Items, BOM views, change orders) |
| Electronics and harnesses | Factory handoff: packages, rule packs, panels, stencils, test, harness package | ELX (board, DRC, connectivity); MEC (harness geometry); ECO (`io/` writers) |
| Connectivity | Machine, printer and CMM protocol mappings; `apps/machine-gateway` | PLT (packaging, serial, certificates); AGT (`api`, Acts) |

**Decision D-MFG-1:** Every manufacturing capability follows the contract's layers: intent in Ingot, heavy search in Wasm components, geometry in Anvil and physics in Flux. *Why:* shops edit intent, algorithms need sandboxed native speed, and shared operations serve CAM, slicing, molding and inspection. *Rejected:* a monolithic CAM engine (privileged code); all-Ingot strategies (inner loops too hot).

**Decision D-MFG-2:** Manufacturing adds no geometry or result types: things are Bodies, Parts and Assemblies, paths are wire Bodies carrying Fields, and results are Fields. *Why:* the UI already paints, diffs, caches and queries these types. *Rejected:* separate stock, toolpath or result types (parallel abstractions).

**Decision D-MFG-30:** A parameter of the material alone is a COV `Material` property, such as Cross–WLF rheology, Tait pvT, solidus, liquidus or cure kinetics. A parameter that depends on machine, mould, tooling or process window, such as melt-to-mould heat transfer, is MFG process data citing COV's model id. *Why:* no parameter may have two owners (R7-42, R10-40). *Rejected:* everything in COV (machine data are not material data); a split per process (melts and alloys straddle it).

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
pub record Workingstep { target: Query, strategy: StrategyCall, station: StationRef, toolpath: Toolpath,
                         comp: CompMode, wear_range: Range<Length> }   // Computer | Control | Wear | ReverseWear
pub record Program     { setups: [Setup], steps: [Workingstep], order: Order }   // ByTool | ByStation
```

**Decision D-MFG-22:** A toolpath is a wire Body with one edge per run of one motion kind, each a polyline or arc-spline with Field samples. A move is addressed by (edge `EntityId`, vertex index), not by a persistent name. *Why:* a finishing path has millions of moves, and an edge per move would carry identity and history each (R2-45). *Rejected:* one edge per move (memory and hashing grow by orders of magnitude); a toolpath type outside `Body`.

Finishing workingsteps declare `comp`, the cutter compensation mode, by default `Computer`. In the other modes posts emit G41 or G42 with the D register. Gouge and collision checks then run at both ends of `wear_range`, so wear adjustments at the control stay verified (R10-13).

**Decision D-MFG-3:** Randomized searches take an explicit `seed` and a counter-based generator, and parallelism runs as a seeded portfolio. Budgets count work units, shown as an estimated time on the reference laptop, and "continue" warm-starts with a larger budget. *Why:* the contract forbids clocks, yet users who expect "run for 10 minutes" still get an estimate (R10-40). *Rejected:* wall-clock limits (non-reproducible); shared-state parallel search (thread-order dependent). (revised in round 3)

Kiln keeps the best portfolio result by (objective, seed), and outputs quantize before locale-free formatting. Outside data enter only as External inputs (prices, offers, machine readings) or Evidence records (part measurements).

```rust
pub enum MfgError {
    Unreachable         { region: Query, reason: ReachReason, fixes: Vec<Fix> },
    Collision           { a: InstanceRef, b: InstanceRef, at: PathParam, block: Option<u32>, fixes: Vec<Fix> },
    Gouge               { depth: Length, at: PathParam, block: Option<u32>, fixes: Vec<Fix> },
    AxisLimit           { axis: AxisId, required: f64, limit: f64, fixes: Vec<Fix> },
    Unsupported         { capability: Capability, controller: ControllerId, fixes: Vec<Fix> },
    Infeasible          { constraint: ConstraintRef, witness: Option<ObjectId>, fixes: Vec<Fix> },
    OutsideEnvelope     { model: ModelId, quantity: QuantityRef, value: f64, fixes: Vec<Fix> },
    MissingData         { what: DataRef, fixes: Vec<Fix> },
    WorkLimit           { limit: base::WorkLimit, best_so_far: Option<ObjectId> },
    OffsetMismatch      { register: OffsetRef, expected: Length, read: Length, tolerance: Length },
    PlanUnapproved      { digest: ObjectId },
    HashMismatch        { diff: ObjectId },       // the semantic NC diff
    ProgramSlotOccupied { number: ProgramNumber, foreign: bool },
    DncSessionPreArmed  { machine: MachineSerial },
}
```

Each `Fix` is a typed edit; no strategy substitutes a tool, direction or material silently. `WorkLimit` is the cacheable `Failure` of KLN's limit catalog, since a search budget is an argument. An Evaluation's `Budget` running out is the Abort `BudgetExhausted` (contract 7.2).

Process profiles declare the representations their hand-off accepts: 3MF accepts implicit and mesh regions, STEP only B-rep, which shops' CAM and CMM read. A part with an implicit fallback region from MEC releases for a STEP process only after conversion within tolerance. No semantic PMI may target such a region (R10-37).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Core manufacturing types | `std::mfg::core` records over Bodies, Fields and Assemblies | Typed compile errors | MFG-O-CORE-1 | 0 |
| Typed failures with fixes | Every `MfgError` carries ranked typed edits | The error itself | MFG-O-CORE-1 | 0 |
| Seeded, budgeted searches | `seed` and work-unit `budget` arguments; seeded portfolios; warm-started "continue" | `WorkLimit` with the best result | MFG-O-DET-1 | 0 |
| Outside data | External inputs and Evidence records, pinned by `ObjectId` in the `CheckOutcome` | `MissingData` naming the input | MFG-O-CORE-2 | 1 |
| Representation acceptance | Accepted representations per process profile; the fallback-region rule | Release blocked, naming region and process | MFG-O-CORE-4 | 1 |
| Label invariance | Plans and costs unchanged when every name is re-randomized | None | MFG-O-LABEL-1 | 1 |
| Toolpath storage | D-MFG-22, target 10⁷ moves under 400 MB | `Infeasible` above the declared move count | MFG-O-CORE-3 | 2 |

## Approval, transfer and physical safety

Simulation proves a program consistent with the model; this path binds the model to the shop floor as far as software can.

1. CI simulates the posted NC text and runs every machining oracle on it.
2. A named person approves the program subject: canonical program digests, machine class, nominal tools, setup sheet, simulation verdicts and `BlockMap`.
3. The program releases as an Item through KLN's manufacturing change order: `Prototype`, `Proven` after a first-article record, then `Released` (D-KLN-38).
4. It reaches a machine by an approved `send_to_machine` plan or, once `Released`, by an operator's request at a qualified machine.
5. The gateway checks the Approval, program number, hash and offsets (D-MFG-24).
6. A person at the device selects the program and starts the cycle after the setup sheet's on-device steps.

**Decision D-MFG-4:** Approval binds to the program subject's `ObjectId`, so a regenerated or edited program never inherits it. The subject binds a machine class (machine package, controller family and version, post version) and nominal tools by T number, never a serial or pocket. *Why:* trust attaches to exactly what was reviewed, while sister machines and reassigned pockets are checked at transfer (R10-08). *Rejected:* approval per workingstep name (survives geometry edits); a serial-and-pocket subject (an approval every shift); signing the `ChangeId` (R3-16). (revised in round 3)

Agents may prepare transfer Acts; only assigned humans approve them or confirm on site. A `Released` program may go to any serial that MFG-O-POST-3's record qualifies for its class, through the pull path below. The operator's request at that machine runs under the release Approval, while a remote push needs its own (contract 7.6).

| Act or method | Effect | Rule |
| --- | --- | --- |
| `send_to_machine` | Stores a typed program or recipe in a device, or stages it for a pull | Never selects, loads or starts it |
| `send_robot_program` | Stores a robot program file in the controller's program store | Never through script, dashboard or real-time interfaces; never writes safety configuration |
| `store_machine_job` | OPC UA `Store` of a job order | The method allowlist below |
| `send_print_job` | Uploads a print job | Start parameters fixed false |
| `start_print` | Starts a material-extrusion print | Contract 7.6: a safety officer's policy per serial, confirmation at the printer |
| `read.machine_data` | Status, offsets, program directory, alarms | A Read method (AGT), never an Act |

`send_to_machine` payloads are typed, each with a device class: `NcProgram`, `DmisProgram`, `BendProgram`, `Recipe` (furnaces, ovens, reflow), `PlacementProgram` and `CutList` (harness machines). Each gets the plan check, canonical hash, read-back where supported and the registry (R10-04). Crucible starts none of these devices, and `unattended_safe` covers none (contract 7.1, 7.6).

ISA-95 Job Control defines eleven job-order methods [ISA-95 Job Control]. Crucible calls `Store` only inside `store_machine_job`, and `Cancel`, `Clear` and `RevokeStart` only on unstarted jobs it stored. Every other method is uncallable (R10-31).

Upload calls can start a device: OctoPrint's `print` and `select` flags [OctoPrint files API], Moonraker's `print` [Moonraker file manager] and PrusaLink's `Print-After-Upload` header [PrusaLink OpenAPI]. Universal Robots' interfaces accept URScript and load and play programs [UR client interfaces], so robot programs move only as files.

Each connector manifest therefore lists its endpoints with fixed parameter values, which the gateway's core enforces outside the connector (R10-01). The EU Machinery Regulation applies from 20 January 2027 with cyber-safety provisions [EU Machinery].

**Decision D-MFG-24:** The gateway sends only payloads whose full SHA-256 appears in a plan approved by its pinned approvers, a signed, log-checkpointed directory. In its own core it also checks a canonical hash on read-back, overwrites only its own programs, checks instance data and captures edits. *Why:* a header hash detects corruption, not substitution (R11-07), controls rewrite formatting (R10-10), and real offsets decide what runs (R4-05). *Rejected:* trusting the server; hashing posted bytes (correct programs mismatch); blocking edits at the control (it cannot). (revised in round 3)

The canonical hash covers the token stream of the semantic NC parser, per dialect, without the header line. `FileRules` declares each control's storage normalizations, and a mismatch reports the semantic NC diff. The header comment carries item, revision and 12 hexadecimal digits of the hash for operators.

Each program Item keeps one number per machine class across revisions, and its subprograms travel with it (R10-11). The gateway overwrites only an earlier revision of the same Item and otherwise fails with `ProgramSlotOccupied`. The setup sheet prints the number, and the approval page states what is replaced.

At transfer the gateway reads offsets, checks D registers against `wear_range` and re-simulates with actual gauge lengths. It then watches every referenced H, D and work-offset register until the program ends (R10-09). A change that fails the check raises an alarm and andon event within 5 s (target) but cannot block the cycle.

Offsets and edits come from vendor connectors, DNC receive or operator entry, and from phase 3 from MTConnect [MTConnect 2.5 Part 3]. An edited program opens a Proposal with its semantic NC diff. Parts made from it get a nonconformance record for disposition (R10-32).

Drip feed is pull-only (R10-02): `send_to_machine` stages the program in the gateway's DNC library and sends nothing. The gateway streams only on a request at the control after commit and after confirmation at its terminal. An already open session fails with `DncSessionPreArmed`.

MFG fills each physical-effect plan with the fields of contract 7.6's approval page, from the device serial to the on-device steps (R10-17).

[[DIAGRAM diagrams/07-manufacturing-program-release.jsx: program release flow · 13 steps from design to control memory]]

Read the flow top to bottom: shaded steps are a person's, red arrows return typed errors, and the dashed arrow is edit capture.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Program subject | `ProgramSubject { programs, machine_class, tools, setup_sheet, verdicts, block_map }`; Approvals sign its `ObjectId` | Changes inside void the Approval; instance data stay outside | MFG-O-SAFE-1 | 2 |
| Manufacturing change lane | MBOM, programs, routings, fixtures, instructions and inspection plans through KLN's MCO (D-KLN-38) | A change to an EBOM definition is rejected | MFG-O-SAFE-1 | 2 |
| Change impact | A design change returns exactly the programs whose targets, setups or `verified_against` revisions changed to `Prototype` | None; the set is reported | MFG-O-SAFE-1 | 2 |
| Transfer Acts and payload kinds | The Act table; typed `send_to_machine` payloads | Refused without an approved subject | MFG-O-SAFE-2 | 2 |
| Restricted print start | `start_print` per contract 7.6 | Refused for other processes, profile-only declarations or remote confirmations | MFG-O-SAFE-2 | 2 |
| Wire-level transfer verification | Manifest allowlists enforced in the gateway core; the OPC UA method allowlist | Other requests dropped and reported | MFG-O-SAFE-3 | 2 |
| Plan check and canonical hash | Full SHA-256 in a plan approved by the pinned set; canonical hash on transfer and read-back | `PlanUnapproved`; `HashMismatch` with the diff | MFG-O-SAFE-2 | 2 |
| Program registry | One number per program Item and machine class; subprograms travel with it | `ProgramSlotOccupied` | MFG-O-SAFE-6 | 2 |
| Transfer-time offset verification | Offsets read, D registers inside `wear_range`, collision re-simulated with actual gauge lengths | `OffsetMismatch` beyond setup-sheet tolerance | MFG-O-SAFE-4 | 2 |
| Offset watch | Checks re-run on each change to a referenced register; alarm within 5 s (target) | Cannot block the cycle | MFG-O-SAFE-4 | 2 (vendor connectors), 3 (MTConnect) |
| Edit capture | Edit watch, DNC receive, Proposal, nonconformance record | Controls without edit signals need an operator declaration | MFG-O-SAFE-4 | 2 |
| Pull-only DNC and drip feed | Serial and Ethernet DNC with flow control, streamed only on a request at the control | `DncSessionPreArmed`; a fault stops the feed, resumed only at a restart point (D-MFG-31) | MFG-O-SAFE-5 | 2 |

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
    macros:  MacroLibrary,               // control-resident macros, under their licences
    files:   FileRules,                  // writing rules and storage normalizations
}
pub record MotionSemantics {
    rapid: Rapid,                        // Linear | PerAxis { rates }
    rotary_rapid: RotaryRapid,           // Shortest | Directional | Unwind
    tcp_in_rapid: Bool, reference_return: ReferenceReturn, cycle_retract: Retract,
    cutter_comp: CutterComp,             // look-ahead blocks, entry rule
    tool_change_envelope: Body,
}
```

**Decision D-MFG-23:** Collision simulation and the independent re-interpreter both execute the posted NC text under the controller's declared `MotionSemantics`, never the pre-post toolpath. An undeclared semantic sweeps a conservative envelope and returns `Unsupported` instead of passing. *Why:* programs crash in motion the control interpolates: dog-leg rapids, unwinding, reference returns, retracts, compensation entry and tool changes (R4-02). *Rejected:* checking the toolpath only; assuming straight rapids, which controls do not promise [Haas G-codes].

Posts convert G0 to G1 at a declared rapid-equivalent feed wherever that envelope comes closer to stock or fixture than the clearance.

**Decision D-MFG-5:** Programs are stored in one form mirroring ISO 14649, each workingstep binding a target, a strategy with tool and technology, and a toolpath. One post engine, a Wasm component, maps it to a dialect through the `Controller` record, data and Ingot hooks. *Why:* STEP-NC export becomes a mapping, blocks trace to workingsteps, and shop post editors work in Ingot (R4-08). *Rejected:* posting from cutter-location files (loses intent); a post per strategy and machine; Rust hooks by default. (revised in round 2)

Hooks run on `on_program_start`, `on_tool_change`, `on_wcs_change`, `on_rapid`, `on_cycle` and `on_program_end`. G-code comes only from this engine, through the `crucible:mfg` `post-processor` world.

**Decision D-MFG-31:** Posts emit a restart point at every workingstep and tool change: a sequence number, then a full modal restatement and a clearance-plane approach. Simulation verifies each entry, the setup sheet lists them, and a restart inside a workingstep is `Unsupported`. *Why:* operators restart by block search after a broken tool or power loss, and a skipped tool call or offset crashes (R10-12). *Rejected:* full runs only (operators restart anyway); restarts anywhere (modal state unchecked).

ISO 6983-1:2009 defines the format and address words, confirmed in 2025 [ISO 6983-1]. Posts read capability flags, not vendor names, with codes from vendor documentation [Haas G-codes; Heidenhain TNC; Siemens Sinumerik; Fanuc CNC]. Where Fanuc names a function without its code, the conformance corpus fixes it, and Mazak gets ISO mode, never Mazatrol.

| Capability flag | Fanuc | Siemens Sinumerik | Heidenhain TNC | Haas |
| --- | --- | --- | --- | --- |
| Tool center point control | G43.4 / G43.5 | TRAORI | M128 or FUNCTION TCPM | G234 |
| Tilted work plane | Tilted Working Plane function | CYCLE800 | PLANE functions | G268 |
| High-speed contour mode | G05.1 Q1 | CYCLE832 | Cycle 32 TOLERANCE | G187 |
| Drilling cycles | G81 to G89 | CYCLE81 to CYCLE89 | Cycle 200 series | G81 to G89 |
| Parametric programs | Macro Executor | R parameters, GUD variables | Q parameters | Macro variables |

A family's post ships only when its crash corpus, captured on the reference shop's controls, matches `MotionSemantics` within tolerance (R10-29). Capture uses a program-test mode that interpolates with the axes still, such as Haas's graphics mode [Haas operation].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Forward and inverse kinematics | `fk` per channel; closed-form `ik` for table-table, head-head and head-table, damped least squares otherwise; every branch | `AxisLimit`; `Unreachable` with the nearest pose | MFG-O-KIN-1 | 2 |
| Rotary indexing and wrapping | 3+1 indexing on A or B; 2D paths wrapped onto cylinders | `AxisLimit` | MFG-O-KIN-1 | 2 |
| Singularities and rotary linearization | Branches minimize rotary travel; points inserted until tip deviation is in tolerance | `Infeasible` with the segment | MFG-O-KIN-2 | 3 |
| Kinematic and spindle limits | Feed limited by per-axis velocity, acceleration and jerk; power and torque against spindle Fields | `Infeasible` with segment and margin | MFG-O-KIN-2 | 2 |
| Motion semantics | D-MFG-23 per controller; G0-to-G1 rule | `Unsupported` if undeclared | MFG-O-SIM-2 | 2 |
| Generic ISO 6983 post | `post(program, machine) -> (NcText, BlockMap)` with arcs, helices, compensation and cycles | `Unsupported { capability, controller }` | MFG-O-POST-1 | 2 |
| Fanuc, Haas, Siemens and Heidenhain posts | 3-axis, 3+1 and 3+2 | As above | MFG-O-POST-1 | 2 |
| Simultaneous 5-axis posts | Four families; TCP, or joint space with inverse-time feed | `AxisLimit` or `Unsupported` | MFG-O-POST-1 | 3 |
| Okuma OSP and Mazak ISO-mode posts | Family offset and cycle conventions | As above | MFG-O-POST-1 | 3 |
| Mitsubishi, Brother and Hurco posts | As above | As above | MFG-O-POST-1 | 4 |
| Post configuration and hooks | Customizations as Ingot data; Ingot hooks; Rust hooks only under contract 4 | Errors name the hook | MFG-O-POST-2 | 2 |
| Restart points | D-MFG-31 | `Unsupported` inside a workingstep | MFG-O-SIM-6 | 2 |
| Macro libraries | Control-resident macros from the control or their maker, in the machine package | `Unsupported { macro }` unless a declared envelope bounds the call | MFG-O-SIM-3 | 2 |
| Post qualification | Shop's proven program against Crucible's on a reference part; corpus captured on physical controls; a record of the serials qualified for the class | Undeclared differences block it | MFG-O-POST-3 | 2 |
| Semantic NC diff and block map | Motion and technology diff ignoring formatting; each block mapped to workingstep, path parameter and feature | None | MFG-O-POST-4 | 2 |

## Tools, stock, setups and workholding

A tool is an Assembly of catalog parts with ISO 13399 properties as typed Quantities [ISO 13399-1]. Vendors publish ISO 13399 data [Sandvik Coromant tool data], and ToolsUnited serves ISO 13399 and DIN 4000 data [Mitsubishi Materials]. Presetter readings and offset tables enter as External inputs.

**Decision D-MFG-6:** In-process stock serves leftover, rest machining and display; gouges are the certified distance between each move's swept envelope and the design B-rep. Stock is an `Implicit` Body on a sparse narrow-band grid unless a pre-phase 2 benchmark shows tri-dexel meeting GP3's tolerances in less memory. *Why:* GP1-sized stock at 5 µm needs about 8 × 10⁹ band cells against a 1 GiB target (R2-24, R10-40). *Rejected:* gouge checks on the grid (resolution-limited); exact B-rep stock (cost grows per move); meshes only (slivers). (revised in round 3)

A setup holds stations, so double vises, tombstones and pallets are ordinary data. `setup_sheet` builds the machinist's Ingot drawing: program number, offsets dimensioned to datums, fixtures, stock and on-device steps. Its tables list tools with gauge lengths and verified offsets, and workingsteps with times, compensation, wear range and restart points.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tool catalog import | ISO 13399 Part 21 data, DIN 4000 mapping and documented tool-library formats → catalog parts | `MissingData` per absent property | MFG-O-TOOL-1 | 2 |
| Tool assembly | `assemble_tool(cutter, holder, extensions, stickout) -> Instance`; full collision Bodies | `Infeasible` on interface mismatch | MFG-O-TOOL-1 | 2 |
| Presetter readings | Length, radius and runout as External inputs per assembly serial | Missing or stale readings flagged | MFG-O-TOOL-1 | 2 |
| Per-machine tool tables | Nominal tools by T number for posts; pockets and H and D values checked at transfer | Conflicting entries fail | MFG-O-TOOL-1 | 2 |
| Cutting data | Vendor data, shop values, mechanistic coefficients and life parameters with source and uncertainty | `MissingData` only without any source | MFG-O-FEED-1 | 2 |
| Tool life | Count-based per edge from as-run records (2); model-based from engagement (4) | Tools past life flagged | MFG-O-TOOL-2 | 2, 4 |
| Blank and hand-off | `stock(kind, material, size or Body, cert)`; setup N's stock is setup N+1's blank | Part outside stock; fixture hits stock | MFG-O-STOCK-1 | 2 |
| In-process and rest stock | `simulate(program) -> (Body, Field<Body, u32>)`; `rest(stock, part, tolerance) -> Body` | `OutsideEnvelope` when the grid misses the tolerance | MFG-O-STOCK-1 | 2 |
| Setups and stations | `Setup { machine, fixture, stations }`; tombstones and pallets | Duplicate work-offset registers fail | MFG-O-SETUP-1 | 2 |
| Setup sheet | `setup_sheet(program, template) -> Drawing` | Tools without gauge data listed | MFG-O-SETUP-1 | 2 |
| Vises and modular fixtures | Catalog parts with jaw stroke and clamping force | `Collision` with toolpaths | MFG-O-SIM-2 | 2 |
| Soft jaws and offset probing | Jaw Bodies offset from the part with their own program; probing cycles that set work offsets | Unreachable points | MFG-O-SETUP-2 | 2 |
| Locating, clamping and jigs | Form closure by contact-wrench rank; clamp forces with friction and Flux deflection (3); weld and assembly jigs | `Infeasible` naming free motions; slip or deflection | MFG-O-SETUP-3 | 2, 3 |

## Milling, drilling and probing strategies

Each strategy is a `toolpath-strategy` Wasm component that turns a setup, region, tool, parameters, tolerance, seed and budget into a `Toolpath`.

OpenCAMLib implements drop- and push-cutter under LGPL-2.1 [OpenCAMLib] with little recent activity [Open Hub OpenCAMLib]. Anvil's `tool_contact` re-implements the algorithms, and OpenCAMLib serves only as a reference oracle.

**Decision D-MFG-7:** Adaptive clearing is a clean-room, engagement-controlled spiral seeded by the medial axis and measured against the true in-process stock. Its bound is maximum engagement angle and chip thickness, which the oracle measures independently. *Why:* vendors document the behavior but not their algorithms, so the measurable bound is the contract. *Rejected:* offset-based pockets (engagement spikes at corners); one vendor's patented method.

1. Compute the medial axis of the region minus the tool radius with exact predicates.
2. Enter by helix or ramp at the vertex of maximal clearance, or at a pre-drilled hole.
3. Grow the cleared region in spiral steps, each solved so engagement against the current stock equals the requested angle.
4. Where the bound cannot hold (necks, corners), switch to variable-radius trochoids.
5. Link passes with tangent-continuous, collision-checked moves inside cleared material, and set feed from chip thinning.

Claim 1 of Boeing's US 9,164,503 needs a pre-roughing slot with curves spiraling out of it, and expires about February 2034 [US 9,164,503]. Its citing documents include toolpath patents of Plethora, D.P. Technology and Siemens. Adaptive clearing ships only after counsel's opinion on the family, other engagement-control patents and every execution path.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Face, pocket, contour and rest (2.5D) | Offset or zigzag depth steps, island-aware, ramp or helix entry; rest passes where material remains | `Unreachable` where narrower than the tool | MFG-O-MILL-1 | 2 |
| Adaptive clearing and trochoidal slotting | D-MFG-7; trochoids varied per period [Li et al. 2025] | `Infeasible` with the achieved maximum | MFG-O-MILL-2 | 2, after the opinion |
| Parallel, scallop and waterline finishing | `tool_contact` to chord tolerance; constant scallop; steep-and-shallow split | Unreachable areas | MFG-O-MILL-3 | 2 |
| Pencil, flowline and isoparametric | Bi-tangent corner passes; iso-curves re-spaced to a scallop bound | Degenerate parameterization | MFG-O-MILL-3 | 2 |
| Deburr, chamfer, engraving and thread milling | Edge-chain passes at size; V-carve from the medial axis; analytic helices | Unreachable edges; `Infeasible` tool fit | MFG-O-MILL-4 | 2 |
| Drilling cycles | Spot, drill, peck, ream, bore, tap, back-bore from MEC's `HoleSpec`; shortest tour | `Unsupported` cycle → expanded moves | MFG-O-MILL-4 | 2 |
| Probing paths | Touch points from the inspection plan; offset writes flagged | Unreachable points | MFG-O-SETUP-2 | 2 |
| 5-axis swarf, multi-axis and barrel finishing | Flank passes on ruled walls; collision-aware tilt from any 3-axis pattern; barrel profiles | `Infeasible`, `Collision` or `AxisLimit` | MFG-O-MILL-5 | 3 |
| 5-axis roughing | Adaptive clearing in tilted frames chosen by access analysis | As adaptive | MFG-O-MILL-2 | 3 |

## Turning, EDM, gears and grinding

GP3's gears are cut by the shop from MEC's gear data table and MFG's inspection plan, while Crucible programs the housings, shafts and blanks (R10-19). MEC owns gear geometry and the ISO 1328-1:2013 grade [ISO 1328-1], and COV owns ratings (contract 13.4). EDM tables come from machine packages; MFG does not model spark physics.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Turning | Revolved Body → XZ profile; rough, finish, groove, part and thread passes with insert clearance | `Infeasible` for non-revolved faces; `Unreachable` undercuts | MFG-O-TURN-1 | 2 |
| Adaptive turning | Constant chip-thickness roughing for heat-resistant alloys [Janus NX 2606] | As above | MFG-O-TURN-1 | 3 |
| Mill-turn | C and Y milling, B tilting, sub-spindle transfer across channels | `Infeasible` with the conflicting window | MFG-O-TURN-2 | 3 |
| Swiss-type and channel balancing | Sliding headstock and gang tools; workingsteps assigned to channels | As above | MFG-O-TURN-2 | 4 |
| Wire EDM | 2-axis rough and skim with tabs; 4-axis taper with synchronized UV paths | `Infeasible` below wire radius plus overburn | MFG-O-EDM-1 | 3 |
| Sinker EDM electrodes | Electrode Body with spark gap, orbit and burn sequence | Typed error when not machinable | MFG-O-EDM-1 | 4 |
| Gear data and inspection | Profile, helix and pitch plans from the record's grade for gear machines or CMMs | As inspection | MFG-O-GEAR-2 | 2 |
| Gear generating | Hobbing and shaping as ISO cycle calls or a builder parameter set, named per family before it ships; power skiving after simultaneous 5-axis collision checking | `Unsupported`; fix: 5-axis gear milling | MFG-O-GEAR-1 | 4 |
| 5-axis gear milling | Flank and root passes from the multi-axis strategies | As 5-axis | MFG-O-GEAR-1 | 3 |
| Grinding, broaching, honing and lapping | Gear and profile grinding with distortion allowance; surface and cylindrical grinding with a specific-energy burn check | `MissingData`; `OutsideEnvelope` | MFG-O-GEAR-1 | 4 |

## Sheet cutting, nesting and press brake

GP4's guards need profile cutting, nesting and press-brake planning in phase 2, each with an output a machine or its software reads (R10-20). MEC owns flat patterns, flat DXF export, the bend-allowance model (`BendRule`, `BendTable`) and self-clinching hardware rules.

Sparrow (MIT) runs guided local search on the jagua-rs collision engine (MPL-2.0) [Gardeyn et al. 2025; jagua-rs]. It matches or beats every best-known ESICUP density, most on SWIM (79.83% against 75.94%), under a 600 s default limit [sparrow].

**Decision D-MFG-8:** Press-brake sequencing searches bend orders with collision checks between the partly bent part, tools and machine. Allowances come from MEC's sheet-metal model, springback from Flux or measurement. *Why:* one search handles every part, and the physics stays with its owners. *Rejected:* rule tables per part family (brittle).

**Decision D-MFG-9:** The 2D nesting Wasm component adopts the sparrow approach on a jagua-rs-style collision engine, with work-unit budgets instead of wall-clock limits (D-MFG-3). *Why:* these are the leading open methods, both in Rust and both buildable for Wasm. *Rejected:* no-fit-polygon heuristics (lower density); closed vendor libraries (unauditable).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Profile cutting and ordering | Laser, plasma or waterjet paths with kerf, lead-ins, micro-joints, pierces, common lines and heat-aware order; a generic ISO 6983 cutting post with codes as `Controller` data, or DXF | `Infeasible` below kerf plus minimum web | MFG-O-CUT-1 | 2 |
| Flat-pattern hand-off | MEC's `export_flat_dxf` (MEC-O-SM-4) with layer convention and bend table per machine or shop | Unmapped entities listed | MFG-O-CUT-2 | 2 |
| Press-brake planning | Bend sequence, tool stations and backgauge (D-MFG-8); allowance tables for MEC's `BendTable`; a bend sheet drawing with bent STEP and flat DXF (2); native bend programs for surveyed families (3) | `Infeasible` with the colliding bend | MFG-O-CUT-3 | 2, 3 |
| Waterjet taper, bevels and punching | Taper and corner compensation (3); 5-axis bevels (4); turret tooling, nibbling, repositioning (3) | `MissingData`; `AxisLimit`; missing tool | MFG-O-CUT-1 | 3, 4 |
| Sheet nesting | `nest(items, sheets, rules, seed, budget) -> Nest` with rotation, grain, spacing, zones and common lines | `Infeasible`; `WorkLimit` with the best nest | MFG-O-NEST-1 | 2 |
| Remnants, associativity and inventory | Remnant Parts; warm-started regeneration; mixed sheets by cost (3) | As nesting | MFG-O-NEST-1 | 2, 3 |

## Feeds, speeds and chatter

**Decision D-MFG-27:** Feeds and speeds default to vendor cutting data or the shop's proven values, labelled by source. The mechanistic model is an advisory check on power, torque, chip thickness and deflection until calibration upgrades the label. *Why:* shops start from vendor tables, and an uncalibrated user would otherwise get `MissingData` everywhere (R4-36). *Rejected:* mechanistic optimization by default (needs calibration); unlabelled values (hide their basis).

With calibrated coefficients, `cutting_conditions(toolpath, material, machine, objective)` returns feed and spindle Fields that maximize removal rate. They are piecewise constant, quantized to the controller increment and labelled with each segment's binding constraint.

MFG's receptance-coupling model gives the tool-tip response from measured spindle FRFs and Flux's modal analysis, or a stored tap test replaces it. Zero-order lobes miss lobes that semi-discretization finds below about quarter-diameter immersion [Altintas et al. 2008].

**Decision D-MFG-10:** `Interactive` lobes use the zero-order solution and `SignOff` lobes semi-discretization, which low immersion, variable pitch and spindle-speed variation always use. *Why:* this matches each method's published validity and keeps interactive updates under one second. *Rejected:* zero-order everywhere (misses low-immersion lobes); time-domain by default (too slow; kept as an oracle).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Source-labelled defaults and calibration | D-MFG-27; calibration cuts fit coefficients with uncertainty | `MissingData` only without any source; poor fits reported | MFG-O-FEED-1 | 2 |
| Advisory constraint check | Chip thinning, mechanistic force and power, spindle curve, roughness, cantilever or Flux deflection | `OutsideEnvelope` outside calibrated ranges | MFG-O-FEED-2 | 2 |
| Feed optimization and tool life | `cutting_conditions`; extended Taylor life per tool-material pair | `OutsideEnvelope`; never an extrapolated feed | MFG-O-FEED-3 | 3 |
| Tool-tip FRF | `frf(tool, machine) -> Field<Frequency, Complex<Compliance>>` | `MissingData` without spindle receptance; fix: tap test | MFG-O-CHAT-1 | 3 |
| Stability lobes and planning | `lobes(frf, coefficients, engagement) -> Field<AngularVelocity, Length>` (D-MFG-10); speed and depth in the stable region | `OutsideEnvelope` at low surface speed; no stable speed reported | MFG-O-CHAT-1 | 3 |
| Chatter feedback | Spindle-load or vibration data flags chatter and updates the FRF | None | MFG-O-CHAT-1 | 4 |

## Machining simulation and NC verification

Simulation interprets posted text under the controller's semantics (D-MFG-23), with conservative-advancement collision detection, so thin parts never slip between samples. The crash corpus plants dog-leg rapids, unwinding, reference returns, wrong retracts, compensation gouges, tool changes and skipped restatements.

**Decision D-MFG-28:** A product NC interpreter, separate from the oracle's, verifies NC from other CAM systems and hand programming, with macros from the machine package's library. Live system variables are typed inputs with ranges whose branches are explored up to a budget, and legacy programs declare `verified_against` revisions. *Why:* shops hold thousands of proven programs that call macros and branch on probes (R4-09, R10-14, R10-15). *Rejected:* one shared interpreter (a shared bug passes both); unknown macros as no-ops; converting legacy NC into workingsteps. (revised in round 3)

Legacy programs import as Assets released as program Items on the same approval path, and programs that write offsets are flagged. Revising a `verified_against` revision returns a legacy program to `Prototype`, and `verify_nc` shows where stock and the new design differ. UIX shows NC text beside the toolpath through `BlockMap`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Material removal and leftover | `simulate(program)` streamed coarse to fine (D-MFG-6); signed stock-to-design distance Field | `OutsideEnvelope` when the grid misses the tolerance | MFG-O-STOCK-1 | 2 |
| Certified gouge check | Per move, certified distance between the swept envelope (`swept_volume`, `tool_contact`) and the design B-rep, at both ends of `wear_range` | `Gouge` with depth and block | MFG-O-SIM-1 | 2 |
| Machine collision and clearance | Continuous detection among links, tool, holder, fixture and stock on every posted move; near-miss Field | `Collision` with block and pair | MFG-O-SIM-2 | 2 (to 3+2), 3 (5-axis) |
| Controller motion | Rapids, unwinding, reference returns, retract planes, compensation entry, tool-change envelopes | `Unsupported` if undeclared | MFG-O-SIM-2 | 2 |
| External NC verification | `verify_nc(nc: Asset, machine, setup, tools) -> NcVerification` per D-MFG-28 | Parse errors; `Unsupported { macro }`; `Undecided` past the budget | MFG-O-SIM-3 | 2 |
| Restart verification | Each restart entry simulated from the tool-change position (D-MFG-31) | `Collision` or `Gouge` naming the restart | MFG-O-SIM-6 | 2 |
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

Native designs need no recognition, since Ingot features know their holes and pockets. Imported B-reps go through rule-based matching and a learned panoptic segmenter whose targets a person or agent confirms. AAGNet reaches 97.44% panoptic quality on MFInstSeg, and FeatureFox exceeds 0.9 with about 250 parts [FeatureFox].

**Decision D-MFG-34:** Learned recognizers train only on data licensed for commercial use of the weights, chiefly parts Crucible generates and labels from their features. Other datasets are benchmarks only; AAGNet's repository states no terms for MFInstSeg [AAGNet]. *Why:* the weights ship in a commercial product, and generated parts carry exact labels. *Rejected:* datasets of unclear licence (unshippable weights); no learned recognizer (targets by hand).

Agents program as people do: Ingot on a branch, every oracle in CI, then a Proposal with cycle-time and tool-count deltas. CloudNC presents CAM Assist output as a draft to review [CloudNC CAM Assist], and NX 2606 suggests strategies [Janus NX 2606; Siemens Lambda Function].

STEP-NC is ISO 14649, in parts for process data, milling, turning, tools, EDM and additive [ISO 14649 catalog]. AP238 edition 3 (ISO 10303-238:2022) adds geometry, GD&T and kinematics [ISO 10303-238; STEP Tools AP238e3]. G-code stays the shop-floor output.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Incremental regeneration and diff | Only affected workingsteps recompute; geometric and technology diffs painted on geometry | `ResolveError` per lost target | MFG-O-PROG-1 | 2 |
| Templates, matching and setup planning | Ingot templates ranked by applicability predicates; targets grouped by access direction into setups | No match typed, never a silent default; `Unreachable` | MFG-O-PROG-2 | 2 |
| Target recognition | Rule-based (2) and learned (3) proposals under D-MFG-34; CPU inference with pinned weights | Unconfirmed targets never drive toolpaths | MFG-O-PROG-3 | 2, 3 |
| Agent-proposed programs | Branch, CI, Proposal, human Approval | Agents cannot approve, commit transfer Acts or edit oracles | MFG-O-PROG-4 | 2 |
| STEP-NC | ISO 14649 parts 10, 11, 12, 111 and 121 and AP238 through ECO's codec (3); parts 13, 14 and 17 (5) | `Unsupported` per workingstep; never invents feeds | MFG-O-PROG-5 | 3, 5 |

## Additive processes and build preparation

ISO/ASTM 52900:2021, confirmed in 2025, is the vocabulary standard [ISO/ASTM 52900]. Its seven categories, first formulated by ASTM F42 [Loughborough AMRG], share one pipeline: build, orient, pack, support, simulate, compensate, slice, emit.

| Category | Layer output | Phase |
| --- | --- | --- |
| Material extrusion (FFF, pellet, continuous fiber, concrete) | 3MF hand-off (1); G-code for Marlin, Klipper and RepRapFirmware, binary G-code (2) | 1, 2 |
| Powder bed fusion (laser, electron beam; metal, polymer) | 3MF for the bureau's build-preparation software (1); own scan vectors once a machine partner accepts an open vector format (4) | 1, 4 |
| Vat photopolymerization (SLA, DLP, mSLA) | Layer images with exposure | 2 |
| Material and binder jetting | Voxel or image stacks per material; layer bitmaps | 3 |
| Directed energy deposition | NC programs on the machining stack | 3 |
| Sheet lamination | Cut paths plus machining programs | 5 |

**Decision D-MFG-11:** The AM pipeline slices the design Body directly in any representation, never through an STL, with an `ErrorBound` per slice. *Why:* triangulating a dense lattice is the bottleneck of conventional build preparation, and direct slicing removes it and the facet error. *Rejected:* mesh-only pipelines (memory blow-up, faceting).

**Decision D-MFG-25:** Until Crucible's slicer passes its comparison, builds go as 3MF to the bureau's build-preparation software for GP2 (contract 13.1) or the user's slicer. FFF 3MFs carry plates, orientation, modifiers and settings, which PrusaSlicer, OrcaSlicer and Bambu Studio read [PrusaSlicer 3MF; OrcaSlicer 3MF; Bambu Studio CLI]. *Why:* incumbent processors carry years of machine and material profiles (R4-13, R10-23). *Rejected:* Crucible's slicer first (unproven); linking an AGPL slicer (contract 7.7). (revised in round 3)

A person's uncontrolled export to a local slicer is an audited local write, not an Act (contract 7.6, R12-16). The bureau's file-acceptance test (contract 13.2) covers a Beam Lattice 3MF, a triangle 3MF and a sliced build. Devices lacking a required extension must refuse the file [3MF Beam Lattice; 3MF Core], so GP2 may also ship as a mesh 3MF.

A 100 mm part with 2 mm cells has about 1.25 × 10⁵ cells, or 10⁸ triangles at 10 µm chordal error (estimate). GP2's mesh export therefore targets at most 2 × 10⁷ triangles in a 3MF under 500 MB, which bounds its lattice density. Its gate 3MF comes from the tagged run build (contract 13.1).

Crucible's slicer serves what only it does: direct slicing of implicit lattices and Field-driven infill. It becomes the FFF default only after matching the reference slicers on the thin-wall corpus and print time. Binary G-code follows libbgcode's published format, without linking the AGPL code [libbgcode].

```
use std::mfg::am::{build, orient, pack, supports, compensate, slice_build}

let plate = build(printer: shop::pbf_ti64_400, parts: [bracket.qty(12)])
    |> orient(objectives: [support_volume, distortion, face_quality(bracket.face(mount))])
    |> pack(spacing: 3mm, seed: 7)
    |> supports(style: block_lattice, critical_angle: 45deg)
    |> compensate(model: inherent_strain, max_iterations: 4, tolerance: 0.1mm)   // phase 2
    |> slice_build(layer: 30um)
plate.require(predicted_deviation(plate) < 0.1mm)
```

**Decision D-MFG-12:** 3D packing adopts spectral packing: FFT correlation of voxel grids for collisions, plus a translational removability check [Cui et al. 2023]. The correlation is `anvil::correlate_grids` with exact integer counts, fixed-point scores and ties broken by grid index. *Why:* it is the best published density-speed trade-off, and integer counts make placements bit-identical. *Rejected:* bounding-box packers (low density); floating-point FFT unchanged (platform-dependent argmin flips).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Orientation | `orient(part, printer, objectives, seed) -> [ParetoOrientation]` over support, height, critical faces, distortion, peel area and anisotropy | Reports the front; never picks without weights | MFG-O-AM-1 | 1 |
| Build hand-off | D-MFG-25 3MF for a named slicer or the bureau's software; a mesh 3MF within GP2's budget where Beam Lattice fails | Unreadable settings and extensions listed | MFG-O-AM-2 | 1 |
| Plate nesting and 3D packing | Footprint nesting (D-MFG-9); `pack(parts, volume, rules, seed, budget) -> Assembly`, interlock-free (D-MFG-12) | `Infeasible` when a part exceeds the volume | MFG-O-AM-3 | 2 |
| Supports | Tree supports (extrusion); point supports with peel and island checks (vat); block, line, cone and lattice supports (metal PBF) | Unsupported overhangs and islands with fixes | MFG-O-AM-4 | 2 |
| Labels and serials | Engraved or embossed identifiers linked to `repo` serials | Face too small | MFG-O-AM-4 | 2 |

## Slicing, lattices, process simulation and DfAM

Variable-width perimeters follow Kuipers and colleagues [Kuipers et al. 2020], and curved layers the quaternion-field framework of Zhang and colleagues [Zhang et al. 2022]. PrusaSlicer, OrcaSlicer and CuraEngine are AGPL-3.0 [PrusaSlicer; OrcaSlicer; CuraEngine], so they serve only as reference oracles. MFG checks MEC's lattices against printer limits and writes them without meshing.

GP2's strut checks need as-built struts in phase 1 (contract 13.4, R7-06). Bureau coupons give, per strut diameter and angle, the as-built diameter and scatter, waviness over the radius of gyration and strut test data. COV builds strut-scale Materials and its strut imperfection regime variable from them.

**Decision D-MFG-13:** Distortion compensation inverts the simulated displacement Field and applies it with `anvil::deform`, iterating until the predicted shape is in tolerance. *Why:* it is the contract's "Fields driving geometry" mechanism and leaves the design Body untouched. *Rejected:* mesh morphing at export (loses associativity and the B-rep).

FLX owns inherent-strain prediction, phase 2 in contract 13.4, as a declared sequence (R7-07):

1. Layer-group activation of part and supports, the supports a homogenized lattice of calibrated stiffness.
2. Baseplate cut, then support removal.
3. Optional stress relief, which scales the inherent strain by a calibrated relaxation factor.

MFG supplies each step's data from coupons, such as cantilevers cut from the plate. Inherent strain lumps each layer's history into a strain set from such coupons [Setien et al. 2019], so it holds only for its calibration. Phase 1 predicts no distortion for GP2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| DfAM checks | Wall and detail size from `anvil::thickness`, overhang, bridging, trapped powder or resin, drain holes, strut and wall thickness (1); thermal mass, slender features, support removal, allowance (2) | Located failures with fixes | MFG-O-AM-5 | 1, 2 |
| As-built strut calibration (metal PBF) | Diameter and scatter, waviness over radius of gyration and strut-specimen data per machine, alloy and parameter set | `MissingData` for an uncalibrated diameter or angle | MFG-O-AM-12 | 1 |
| Conformal lattices | Cells mapped by a parameterization | Cells above a distortion bound | MFG-O-AM-5 | 2 |
| Planar slicing | `anvil::section` per layer on any representation, with `ErrorBound` (D-MFG-11) | Open contours name the faces | MFG-O-AM-6 | 2 |
| Extrusion and vat layers | Adaptive layer height, variable-width perimeters, Field-driven infill, seams and travel; anti-aliased masks | Regions thinner than a bead; `OutsideEnvelope` | MFG-O-AM-6 | 2 |
| PBF scan vectors | Hatch, stripes, islands and skins in 3MF Toolpath or another open format a named machine partner accepts | `Unsupported` without a partner format | MFG-O-AM-6 | 4 |
| Multi-material, DED and curved layers | Per-region materials from Fields (3); bead paths on the machining stack (3); isosurface layers (4) | `MissingData`; `Collision`; `Infeasible` order | MFG-O-AM-6 | 3, 4 |
| Inherent-strain distortion | Coupon data for FLX's sequence: layer-group strains, support stiffness, relaxation factor | `OutsideEnvelope` outside the calibrated set | MFG-O-AM-7 | 2 |
| Recoater risk and thermo-mechanics | Recoater clearance (2); DED bead activation with plasticity (3); PBF layer thermo-mechanics on COV's model (4) | `OutsideEnvelope` at melt-pool scale | MFG-O-AM-7 | 2, 3, 4 |
| Compensation | Iterative pre-deformation (D-MFG-13), sent as geometry to the vendor's build processor | `Infeasible` with the residual | MFG-O-AM-8 | 2 |
| Cure, sintering and warp | Vat working curve (2); binder-jet shrinkage and FFF warp (4) | `MissingData` without constants; `OutsideEnvelope` | MFG-O-AM-9 | 2, 4 |

## Printers, 3MF and print transfer

Printer profiles are packages: printer Assembly, parameter sets with envelopes, material profiles and calibration prints such as OrcaSlicer's [OrcaSlicer]. The 3MF suite is ISO/IEC 25422:2025, and the Toolpath extension, updated on 17 September 2026, is still a draft [3MF specifications; 3MF Toolpath].

Every printer is reached through the machine gateway, and status is a Read. The phase 2 gate's extrusion part goes to an open-firmware printer through `send_print_job` (contract 13.1).

Bambu Connect "removes slicing functions while enabling remote control and print initiation" [Bambu Lab 2025]. Developer Mode leaves MQTT, live stream and FTP open without vendor support [Bambu Developer Mode]. There `send_print_job` uploads over FTP only, with the owner's acceptance in the site policy; otherwise a person starts the job in Bambu Connect (R10-35).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| 3MF production write | Build items, object references, UUIDs, materials, beam lattices and thumbnails through ECO's writer | Unsupported constructs listed, never dropped | MFG-O-AM-10 | 1 |
| Further 3MF extensions | Toolpath (2); Boolean, Volumetric and Secure Content (3), through ECO's writer | Written only where the target declares support | MFG-O-AM-10 | 2, 3 |
| Binary G-code | bgcode from the published description | Unsupported blocks listed | MFG-O-AM-11 | 2 |
| Printer profiles and calibration | Profiles with envelopes; calibration prints and coupons | `OutsideEnvelope` outside the profile | MFG-O-AM-11 | 2 |
| Print transfer and control | `send_print_job` to OctoPrint, Moonraker and PrusaLink with start parameters fixed false, and to Bambu by Developer Mode FTP or Bambu Connect; `start_print`; cancellation | Never retried without a person; starts refused without contract 7.6 conditions | MFG-O-SAFE-2 | 2 |

## Molds and injection molding

Tooling is designed in Ingot as Parts and Assemblies, the process runs as Flux forms, and results are Fields. MEC's `split_mold` returns core, cavity and side-action Bodies (phase 3), and MFG supplies the shrink Field.

**Decision D-MFG-14:** Tooling geometry derives from the part by Anvil operations and stays associative; tool-only edits (shutoffs, vents, cooling) are features on the derived Body. *Why:* associativity is the main lever against late tooling changes. *Rejected:* exported tool geometry edited separately (breaks the single model).

**Decision D-MFG-15:** `SignOff` fill, pack and cool run 3D octree solvers with a level-set front, eight cells across the half-thickness and a warpage estimator. `Interactive` uses mid-surface Hele-Shaw within three regime variables: h/L_flow ≤ 0.1, |∇h| ≤ 0.1, and 2h from gates, roots, steps and the front. *Why:* gap-averaged flow fails where orientation and frozen layers form (R7-29, R7-09), and Hele-Shaw answers thin walls in seconds (R1-41). *Rejected:* Hele-Shaw only (invalid for thick parts); 3D only (too slow interactively). (revised in round 3)

Regions failing the third variable are `Flag` and need the 3D model at `SignOff`. Phase 3 calibrates the thresholds on a step plate and a ribbed plaque; until then the zone is `Extrapolated`. GP5 at eight cells across a 1 mm half-thickness over 5 × 10⁴ mm² of wall needs about 5 × 10⁷ cells (estimate). It runs on a team server (target).

**Decision D-MFG-29:** Short-fibre orientation uses ARD-RSC with a fitted closure [Phelps and Tucker 2009; Wang et al. 2008], with Folgar–Tucker as COV's L0 level. Warpage follows residual stress along the pvT path with frozen-layer pressure, mold constraint and crystallization kinetics. *Why:* measured orientation evolves more slowly than Jeffery-based models predict [Wang et al. 2008], and pressure history dominates warpage (R1-41). *Rejected:* Folgar–Tucker alone; thermal shrinkage alone.

A short shot is a result, an unfilled-region Field with its frozen front; non-convergence returns `Infeasible` with the last converged time.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Moldability and pull direction | Draft, undercut, thickness and sink-risk Fields; directions ranked by undercut area and side actions | Located failures; ties reported | MFG-O-MOLD-1 | 3 |
| Parting, shutoffs, core and cavity | Parting line from silhouettes; ruled or extended surfaces; `split_mold` with MFG's anisotropic shrink Field | `Infeasible` with the open loop; `ResolveError` | MFG-O-MOLD-1 | 3 |
| Side actions, ejection and mold base | Slides and lifters with travel; ejector pins with force; standard plates as catalog parts | `Collision` during opening; pin overload | MFG-O-MOLD-2 | 3 |
| Gates, runners, cooling and venting | Gate type and location, runner balancing, Pareto gate search; drilled, baffled and conformal channels; vents at air traps | Unmet constraints; steel-distance violations; unvented traps | MFG-O-MOLD-2 | 3 |
| Fill, pack and cool | D-MFG-15 with COV's Cross-WLF and Tait pVT, gate freeze and cyclic mold conduction | `OutsideEnvelope` outside the melt range or Hele-Shaw regime; jetting out of scope | MFG-O-MOLD-3 | 3 |
| Fibre orientation, warpage and compensation | D-MFG-29; cavity pre-deformation by D-MFG-13 | `OutsideEnvelope` for long fibres; `Infeasible` when compensation stalls | MFG-O-MOLD-4 | 3 |
| Molding variants | Gas-assist, co-injection, overmolding, injection-compression, foaming | Each declared separately | MFG-O-MOLD-3 | 4 |

## Casting and bulk forming

Rule-based design precedes simulation, whose solidification comes from COV's physics package. HPDC jets atomize at gate velocities beyond reach (OOR-8), so above the breakup Weber number filling is `Extrapolated`. Niyama was validated on WCB steel, A356 and AZ91D [Carlson and Beckermann 2009], and porosity is predicted only for calibrated alloys.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Patterns, gating and risers | Pattern with shrinkage, draft and allowance Fields, cores; ingates from fill time and pressurization ratio; risers by modulus and feeding distance | Velocities above the ingate limit; `Infeasible` with the isolated hot spot | MFG-O-CAST-1 | 4 |
| HPDC die and shot profile | Die halves, slides, overflows, vacuum vents, trim die; phases, switch-over, intensification | `OutsideEnvelope` beyond the machine | MFG-O-CAST-1 | 4 |
| Filling, solidification and die cycling | Free-surface filling with the Weber regime; enthalpy with fraction-solid curves; cyclic die steady state | `Extrapolated` above breakup (OOR-8); uncalibrated alloys | MFG-O-CAST-2 | 6 |
| Porosity and defect indicators | Dimensionless Niyama; air entrapment and cold shuts | Calibrated alloys only | MFG-O-CAST-2 | 6 |
| Investment casting and hot tears | Wax trees, shells, radiation cooling; solidification stress | `OutsideEnvelope` for directional and single-crystal growth | MFG-O-CAST-2 | 6 |
| Forging and extrusion | Preforms and dies with flash, load and die stress by rigid-viscoplastic FEM; extrusion dies by ALE flow | Laps and folds flagged; seam welds out of scope | MFG-O-BULK-1 | 5 |
| Thermoforming | Molds with draft and vents; membrane thickness; trim programs | `OutsideEnvelope` outside the tested range | MFG-O-BULK-1 | 4 |
| Blow, rotational and compression molding | Parison and preform design; deposition wall thickness; SMC and BMC charge and flow | Rotational results flagged indicative | MFG-O-BULK-1 | 5 |

## Sheet forming

MEC owns sheet-metal design; MFG owns how sheet parts are made.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tube bending | Rotary-draw sequence, tooling, collision, thinning, ovality; springback from measured tables | `Collision` or `Infeasible` with fixes | MFG-O-FORM-1 | 3 |
| Blank development and formability | One-step inverse FEM; incremental shell FEM for thinning, strains and forming-limit margin | `OutsideEnvelope` outside calibrated curves | MFG-O-FORM-2 | 5 |
| Die faces, stages and progressive dies | Binder, addendum, beads, trim and flange lines; stages with tonnage; strip layout | `ResolveError`; `Infeasible` naming the stage | MFG-O-FORM-2 | 5 |
| Springback, compensation and robustness | Unloading analysis; compensation by D-MFG-13; capability Fields under variation | `OutsideEnvelope` without kinematic hardening | MFG-O-FORM-2 | 5 |
| Roll forming and hydroforming | Flower pattern and passes; pressure and feed paths with burst and wrinkle margins | Exceeded limits reported | MFG-O-FORM-2 | 5 |

## Welding, joining and composites

MEC owns weld joints, symbols and laminate design; MFG owns procedures, sequences, paths, distortion and laminate manufacture. Records follow ISO 15609-1:2019, ISO 15614-1:2017 with Amd 1:2019 and ISO 9606-1:2012 [EVS welding], or AWS D1.1 and ASME IX. MEC's `Weld` quality level (ISO 5817 or AWS D1.1) drives inspection plans.

Weldment Parts carry MEC's `execution_class` under EN 1090-2:2018+A1:2024 [EVS EN 1090-2] (R10-42). MFG derives the quality level, NDT extent and ISO 3834 part from it; phase 5 enforces it for GP8.

**Decision D-MFG-32:** In frames Flux models as beams, weld shrinkage enters as joint loads from inherent strain on local joint models that `flux::mark_reduction` keeps solid. Phase 2 strains come from coupons per joint type, thickness, process and heat input. *Why:* inherent strain is an initial strain in an elastic analysis of the joint [Murakawa et al. 2010], which a beam lacks (R7-20). *Rejected:* inherent strain on beams (undefined); waiting for phase 4's transient model.

`tightening` picks torque-angle or yield control when MEC's preload range is narrower than torque control's scatter.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Weld procedures and pass plans | WPS linked to PQR and welder records; heat input and pass plans; visual and NDT plans per quality level and execution class | `MissingData` for unqualified combinations; `OutsideEnvelope` | MFG-O-JOIN-1 | 2 |
| Weld sequencing and structure-scale distortion | Order and direction minimizing distortion and travel; inherent strain on shells or solids, joint loads on beams (D-MFG-32) | `OutsideEnvelope` outside the coupons' heat input and thickness | MFG-O-JOIN-2 | 2 |
| Joint-scale weld simulation | Transient thermo-elasto-plasticity with a moving heat source [Goldak et al. 1984] calibrated by macrograph | Long runs flagged at `Interactive` | MFG-O-JOIN-2 | 4 |
| Robot weld paths | Torch angles, weaving and seam tracking | `Collision`, `Unreachable` | MFG-O-ASM-4 | 3 |
| Fastening specification | Method, target with scatter, sequence, tool and audit from MEC's preload range | `Infeasible` when scatter misses the range | MFG-O-JOIN-3 | 2 |
| Riveting, clinching and bonding | Fastener, pitch, edge distance and access; bead paths, bondline, preparation and cure | Rule failures; `MissingData` without adhesive data | MFG-O-JOIN-3 | 3 |
| Composite plates, plies and layup | Plate machining (3); MEC plies nested with grain; ordered plies with projector data (4) | Missing ply references | MFG-O-JOIN-4 | 3, 4 |
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
| Heat treatment and HIP | Recipes with hardness and case-depth targets (2); HIP and AM stress relief (3); distortion from COV's transformation models, compensated (6) | `OutsideEnvelope` when COV misses the alloy | MFG-O-TREAT-2 | 2, 3, 6 |
| Plating, paint and powder coat | Film thickness, cure, masking and spray paths (4); plating current distribution from COV's package (5) | `OutsideEnvelope` for unmodeled chemistry | MFG-O-TREAT-1 | 4, 5 |

## Electronics and harness manufacturing handoff

MFG owns the factory handoff: package choice, capability records and rule packs, panels, stencils, test strategy and the harness package. ELX owns the board model, its DRC engine, the IPC-2152 screen, `test_point` features, functional spacing and the coating record; ECO owns the writers. A board passes DFM for a specific fabricator and class.

**Decision D-MFG-16:** The default fabrication package is IPC-2581 revision C with Gerber X2 layers (revision 2026.05), XNC drill, the job file and an IPC-D-356 netlist. ODB++ from ECO's writer (phase 3) serves houses that read it, and ECO owns every writer. *Why:* IPC-2581C is open and carries DFX feedback [IPC-2581; IPC-2581C], Gerber is the de facto standard [Ucamco Gerber], and fabricators test against a netlist (R10-34). *Rejected:* Gerber only (no stackup or DFX); ODB++ only through a licensed translator, though an open tool writes it [KiCad 9.0]. (revised in round 3)

Boards carry `fab_class` and `assembly_class` (Class 1, 2, 3 or 3/A) that select rule packs citing IPC-6012F, IPC-A-600M, IPC-A-610J and J-STD-001J [IPC store]. Via classes carry an IPC-4761 protection type (tented, plugged, filled or capped), which the drawing notes and a via-in-pad rule checks.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Fabrication package | Per fabricator (D-MFG-16): IPC-2581C, Gerber X2, XNC drill and route, job file, IPC-D-356, impedance and stackup tables, or ODB++, through ECO's writers | Unsupported constructs listed | MFG-O-PCB-1 | 3 |
| Assembly package | Placements, Gerber X3, assembly BOM with approved manufacturers, rotation conventions per line, drawings with ELX's coating keep-outs | `MissingData` without a rotation convention | MFG-O-PCB-2 | 3 |
| Classes, rule packs and fabrication drawing | Classes select annular ring, plating and acceptability rules; drawing notes for class, IPC-4101 material, finish, via protection, impedance and acceptance | A board without a class blocks the package | MFG-O-PCB-3 | 3 |
| Panels, stencils and reflow | Rails, tabs, V-score, fiducials, coupons, nested mixed panels, tab stress in Flux; stencil apertures by area ratio; reflow limits from paste and part ratings | `Infeasible` beyond line limits; apertures below ratio; `OutsideEnvelope` | MFG-O-PCB-4 | 3 |
| Fab DFM and assembly DFA | Rule packs on ELX's DRC (annular ring, spacing, slivers, acid traps, copper balance, via-in-pad; part spacing, tombstoning, rework access); DFX records | Located failures with fixes | MFG-O-PCB-5 | 3 |
| Test access and programs | Coverage, probe spacing and fixture side; a Proposal adding `test_point` features; flying-probe and bed-of-nails data; boundary scan | Untestable nets, including points under coating | MFG-O-PCB-6 | 3 |
| Box build | Board Instances feed sequence planning and work instructions | As assembly | MFG-O-ASM-1 | 3 |
| Harness manufacturing package | 1:1 formboard from MEC geometry; connector face views with cavity numbers; cut list with gauge, colour and lengths; terminals and seals with crimp height and pull force; splices, markers, coverings; test netlist; IPC/WHMA-A-620F class [IPC store] | `MissingData` for terminals without crimp data | MFG-O-HARN-1 | 4 |

## Assembly and work instructions

**Decision D-MFG-17:** Assembly planning is disassembly search over continuous collision-free motions, with gravity stability checked by Flux rigid-body contact, giving an AND/OR precedence graph. *Why:* disassembly handles tight clearances and fasteners, and one graph feeds balancing, instructions, repairability and recyclability. *Rejected:* direction-cone heuristics (fail on screws); hand-entered precedence (not regenerated).

Robots are Machines sharing kinematics, collision and posts with machine tools. Programs are proved in manual reduced-speed mode and never change safety-rated zones or speeds (ISO 10218-1:2025, ISO 10218-2:2025) [EVS ISO 10218-1; EVS ISO 10218-2]. Each family's machine package states its file type and loading path (R10-43); FANUC TP needs the ASCII Upload option or Roboguide compilation [RoboDK Fanuc].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Disassembly, sequences and fastening steps | `disassemble(assembly, seed, budget) -> PrecedenceGraph`; sequences minimizing reorientations and unstable states; fasteners as steps with tool and torque | `Infeasible` listing interlocked Instances; `MissingData` | MFG-O-ASM-1 | 2 |
| Tool and hand access | Swept volumes of tools and hands per step | `Unreachable` with fixes | MFG-O-ASM-1 | 3 |
| Design-for-assembly | `dfa(assembly) -> DfaReport`: separate-part test, handling and insertion difficulty after Boothroyd, Dewhurst and Knight [Boothroyd et al. 2011], efficiency index against the theoretical minimum time [DFMA DFA] | Instances without data listed as undetermined | MFG-O-ASM-2 | 2 |
| Work instructions | Steps with exploded views, tools, torques, checks and safety notes; glTF 2.0 with an accessible viewer and PDF (2); OpenUSD and locales (3) | Steps without a view; missing translations | MFG-O-ASM-3 | 2, 3 |
| Robot programming | Targets, external axes and positioners, collision-free seeded planning; posts to ABB RAPID, KUKA KRL, FANUC TP, Yaskawa INFORM and URScript [RoboDK post processors; RoboDK KUKA; RoboDK UR], never safety configuration; loading paths; cycle time | `Unreachable`; `WorkLimit`; `Unsupported`, including `AsciiUpload` | MFG-O-ASM-4 | 3 |
| Line balancing | Stations for a takt or takt for stations (3); mixed models, zoning, skills, two-sided lines (4) | `Infeasible` when a task exceeds takt | MFG-O-ASM-5 | 3, 4 |

## Inspection and measurement

MEC owns GD&T semantics and general tolerances; MFG owns measurement, evaluation and reporting. QIF is ISO 23952:2020 [ISO 23952] and DMIS is ISO 22093:2011 [ISO 22093]. A measurement is an Evidence record per characteristic check, read at the Evaluation's evidence watermark (contract 2).

**Decision D-MFG-18:** Characteristics are first-class records generated from GD&T with stable identities from provenance; untoleranced sizes take MEC's general tolerance, labelled "general" (R10-21). Plans, programs, results, SPC, FAI and PPAP reference those identities. *Why:* a design diff then names exactly which characteristics changed, which drives partial FAI. *Rejected:* balloon numbers as identity (renumbering breaks traceability); documents as truth (they drift). (revised in round 3)

**Decision D-MFG-26:** Balloon labels are allocated once per characteristic identity, never reused and renumbered only on command. Each release produces the ballooned PDF that Form 3, plans and reports cite. *Why:* AS9102 revision C defines ballooned characteristics and documents [IAQG 9102C], and shops need labels that stay put (R4-14). *Rejected:* labels as identity; renumbering per release (breaks open reports).

**Decision D-MFG-33:** Conformance decisions use the lab's expanded uncertainty U: `Pass` inside the zone reduced by U, `Fail` outside it enlarged by U, else `Undecided`. Phase 1 runs this for GP1 and GP2, with results from QIF 3.0 or a CSV by balloon label. *Why:* ISO 14253-1:2017 requires uncertainty to count [ISO 14253-1], and the phase 1 gate measures both parts (R10-03). *Rejected:* acceptance on the reading alone; waiting for phase 3's CMM work (no gate verdicts).

A customer PDF without a model imports as a controlled document whose balloons are placed by hand or by an agent Proposal. JCGM 100:2008 with Amendment 1 (2026), 101, 102 and 106 cover uncertainty, Monte Carlo, multiple outputs and conformity [BIPM JCGM].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Characteristics and balloons | Dimensions, controls, general tolerances, notes and special characteristics with D-MFG-26 labels: size, location, orientation, form and profile (1), the rest and foreign drawings (2) | Unresolved characteristics; label conflicts fail release | MFG-O-INSP-1 | 1, 2 |
| Results as Evidence records | QIF 3.0 Results or CSV by balloon label (1); DMIS from Crucible's CMM programs (3); one signed record per characteristic | Unmatched results reported | MFG-O-INSP-3 | 1, 3 |
| Conformance decisions | D-MFG-33 with the lab's stated U | `Undecided` in the guard band; `MissingData` without U | MFG-O-INSP-5 | 1 |
| Method selection and sampling | Method by uncertainty ratio and %GRR; point counts for a target uncertainty | `Infeasible` when no method meets the ratio | MFG-O-INSP-2 | 3 |
| CMM paths and programs | Collision-free paths with articulating heads; DMIS and QIF Plans; on-machine probing through posts | `Unreachable` points with fixes | MFG-O-INSP-2 | 3 |
| Feature evaluation | Least squares, minimum zone, inscribed and circumscribed fits; datum frames; tolerances on scans | `OutsideEnvelope` for thin coverage | MFG-O-INSP-4 | 3 |
| Scan registration and deviation | Robust or datum-constrained alignment; signed deviation Field with scanner uncertainty | Residual reported; gaps as regions | MFG-O-INSP-4 | 2 |
| Uncertainty budgets | Typed budgets with Flux sensitivities (2); JCGM 101 Monte Carlo and JCGM 106 guard bands (3); virtual CMM (4) | `MissingData` without error models | MFG-O-INSP-5 | 2, 3, 4 |

## Quality records: SPC, MSA, FAI and PPAP

Process profiles declare Cp and Cpk per process and feature class, which MEC's default distribution reads (D-MEC-28). A first-article record signs the program revision, serials and one passing Evidence record per characteristic (R10-16). It moves a program to `Proven` (D-KLN-38), and AS9102 forms render it from phase 3.

Per IAQG's 9102 revision C summary, FAI is not product acceptance and each item needs its own FAI [IAQG 9102C]. AIAG lists PPAP-4 [AIAG PPAP] and the AIAG & VDA FMEA Handbook [AIAG-VDA FMEA].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Process capability profiles | Declared Cp and Cpk (2); computed from SPC data (3) | Unknown capability reported, never assumed | MFG-O-QUAL-1 | 2, 3 |
| First-article record | Program revision, machine and part serials, one passing Evidence record per characteristic, signed; partial scope from the design diff | Missing or failing characteristics block it | MFG-O-QUAL-2 | 2 |
| Nonconformance | Records linked to serials, characteristics and dispositions, including parts from programs edited at the control | None | MFG-O-QUAL-2 | 2 |
| SPC | Control charts (X-bar, R, S, individuals, p, np, c, u, EWMA, CUSUM), run rules as data, capability indices with intervals; signals linked to machine, program and tool (4) | `MissingData` below the subgroup minimum | MFG-O-QUAL-1 | 3, 4 |
| Measurement system analysis | Gauge R&R by average and range and by ANOVA, bias, linearity, stability, attribute agreement | `MissingData` below the study design | MFG-O-QUAL-1 | 3 |
| AS9102 and partial FAI | Forms 1 to 3 rendered from the first-article record, BOM, routing and certificates | Missing fields and unmeasured characteristics block the report | MFG-O-QUAL-2 | 3 |
| PPAP, FMEA and control plans | PPAP-4 elements with the retention matrix and customer overlays; PFMEA and DFMEA with action priority; controls and special-characteristic symbols linked to characteristics | Missing elements; uncontrolled special characteristics | MFG-O-QUAL-3 | 4 |

## Cost and sourcing

Crucible costs the actual process plan where one exists and geometric proxies otherwise, so phase 1 costs GP1 by proxies and GP2 from its build.

**Decision D-MFG-19:** Cost is a typed roll-up over the process plan in `Money<C>` with a price date and interval, painted as cost-density Fields. Each estimate states its basis: `parametric`, `planned` or `quoted`. *Why:* one mechanism serves every process and shows the basis and the costly features. *Rejected:* a separate costing database (drifts); single numbers (hide uncertainty); calling the basis a fidelity. (revised in round 2)

Cost elements are material, scrap, machine and setup time, labor, consumables, energy, tooling, overhead and logistics. Prices and rates are dated External inputs, and an amount payable rounds once through ING's `round_minor(currency)` (R9-49). Supplier data leave a tenant only through AGT's Acts to KLN's recipient records.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Parametric cost | Regressions on geometric attributes per process family with stated training data and error | `OutsideEnvelope` outside the training range | MFG-O-COST-1 | 1 |
| Planned cost | `should_cost(part, routing, rates, qty) -> Cost` with `Money` per element, a total interval and a cost-density Field | `MissingData` for unknown rates; never an unflagged default | MFG-O-COST-2 | 1 (AM), 2 (machining, sheet, weld), 3 (molding), 4 (others) |
| BOM roll-up and currency | EBOM query × item cost plus assembly labor; rates as dated External inputs | Items without cost listed; `Money<Eur> + Money<Usd>` fails to compile | MFG-O-COST-3 | 1 |
| Volume curves and target costing | Cost against quantity with tooling breakpoints; targets allocated down the BOM as checks | Failures name the largest contributors | MFG-O-COST-3 | 2 |
| Quote requests | `request_quote` Acts carrying a released package to ECO's partner connectors; quotes return as External inputs | Errors typed; never in evaluation | MFG-O-COST-4 | 2 |
| Suppliers and alternates | Processes, envelopes, materials, tolerances, certifications, capacity; matching to routing steps; form-fit-function alternates | Expired certifications; unchecked alternates blocked | MFG-O-SRC-1 | 2 |
| Make-or-buy, lead time and risk | Plan against quotes with risk and lead-time intervals; single source, geography, lifecycle and compliance per Instance | Missing data reported; unknown scores never low | MFG-O-SRC-2 | 3 |

## Factory connection and digital twin

MTConnect's REST API is "read-only and does not produce any side effects" [MTConnect 2.5]. OPC 40501-1 is at 1.02.0 [OPC 40501-1], OPC 40001-3 at 1.0.1 [OPC 40001-3], and async-opcua (MPL-2.0) links unmodified [async-opcua].

**Decision D-MFG-20:** Machine data enter through native MTConnect and OPC UA adapters outside evaluation, as External inputs signed by the gateway's device key. Both read, and OPC UA calls only the job allowlist, in `SIGNANDENCRYPT` sessions [OPC UA Part 4] with a site-managed certificate trust list. *Why:* reads cannot move a machine, unsecured sessions let anyone call methods (R11-07), and signed inputs keep evaluation deterministic. *Rejected:* vendor protocols in the core (they are connectors); live data in evaluation; OPC UA writes (a write can start motion). (revised in round 3)

The gateway is `apps/machine-gateway`, owned by MFG and packaged by PLT (contract 12, R10-28). It connects outbound only, runs connectors out of process behind its egress filter, and sits in an OT zone after IEC 62443-3-3:2013 [IEC 62443-3-3]. It signs inputs with a TPM 2.0 key; without one its readings carry `data_untrusted` and serve no `SignOff` check.

MFG maps MBOM, routings and work orders out through ECO's `erp-connector` and `mes-connector` from phase 2 (D-ECO-30, R10-33). Costs, lead times, inventory, status, scrap and labor return as External inputs. The digital twin is the design plus as-planned, as-run and as-measured records per serial.

[[DIAGRAM diagrams/07-manufacturing-factory-feedback.jsx: factory feedback loop · as-planned, as-run and as-measured back to the model]]

Read the loop clockwise: gateway readings become signed records, then per-serial comparisons, and only an approved calibration Proposal changes the model.

AOUSD announced OpenUSD Core Specification 1.0 on 17 December 2025 [AOUSD Core 1.0]; USD is an export target, never the source of truth.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Gateway | `apps/machine-gateway`: outbound only, connectors behind its egress filter, safety functions in its core, TPM 2.0 key, offline buffering | Gaps recorded; readings `data_untrusted` without a TPM | MFG-O-FAC-1 | 2 |
| MTConnect and OPC UA adapters | MTConnect observations on axes, spindles, programs, tools and offsets; OPC UA Machine Tools and Machinery models with job orders mapped to routing steps | Schema and security-policy failures typed; partial data marked | MFG-O-FAC-2 | 3 |
| MES and ERP mapping | MBOM, routings and work orders out through ECO's worlds (2); status, scrap and labor back (4) | Mapping errors per field | MFG-O-FAC-3 | 2, 4 |
| MBOM and routings | EBOM-to-MBOM rules as Ingot (phantoms, kits, stations, consumables); routing steps with times and work centers (2); effectivity by serial, date, work order or lot (3) | Unconsumed items; unmapped work centers | MFG-O-FAC-4 | 2, 3 |
| OpenUSD export | Cells as USD layers with joints and prim paths from `EntityId`s, process animation (3); incremental layers (4) | Unsupported constructs listed | MFG-O-FAC-5 | 3, 4 |
| As-built records | Per serial: lots, revisions, operators, KLN deviations, nonconformances, Evidence records, deviation Fields | Gaps flagged, never back-filled with nominal values | MFG-O-FAC-6 | 3 |
| Model calibration | As-run data update coefficients, cycle-time factors and distortion calibration through Proposals | Updates outside declared bounds need human approval | MFG-O-FAC-7 | 4 |
| Product twin export | As-built Assembly with measured Fields for FMI or SSP co-simulation | Missing measurements flagged as nominal | MFG-O-FAC-5 | 5 |

## Sustainability and compliance

ISO 14044:2006, amended in 2017 and 2020 and confirmed in 2022, sets LCA requirements [ISO 14044], and ISO 14040:2006 carries Amd 1:2020 [ISO 14040]. MFG computes cradle-to-gate inventory from the process plan and end of life from the disassembly graph.

ESPR, Regulation (EU) 2024/1781, has been in force since 18 July 2024 [EU ESPR], and Regulation (EU) 2026/1778 sets the registry [EUR-Lex 2026/1778]. The registry opened on 20 July 2026, taking registration "through a web interface or an API" [Transition Pathways DPP]. Decision (EU) 2026/1736 references EN 18216 and EN 18219 to 18223 [EUR-Lex 2026/1736], and Article 10(4) requires an independent back-up [EU ESPR].

**Decision D-MFG-21:** The Digital Product Passport is generated from the released model, as-built records and LCA, with each delegated act a versioned query mapping. `publish_passport` publishes to the economic operator's chosen service and mirrors a back-up to an independent provider; Crucible runs no passport service. *Why:* requirements differ per product group, content must trace to the model, and ESPR requires the back-up (R5-35). *Rejected:* one hard-coded schema; manual forms (drift); a Crucible service (records outside their tenants). (revised in round 3)

Regulation (EU) 2017/821 "will only apply directly to EU-based importers of tin, tantalum, tungsten and gold" [EU conflict minerals]. MFG therefore checks 3TG data for completeness only (R5-34). Regulation packages carry dated lists [ECHA Candidate List], and a missing declaration fails release unless a Waiver covers it (contract 2, R9-15).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Embodied carbon | Global warming potential per BOM line from COV's `EnvironmentalRecord`s (generic factors from phase 2), as per-Instance and density Fields; supplier data override | Generic versus specific flagged | MFG-O-SUST-1 | 2 |
| LCA scope and inventory | Typed functional unit, boundary and allocation; flows from materials, power, consumables, scrap and transport | Missing scope fails to compile; flows without factors never zeroed | MFG-O-SUST-1 | 3 |
| Impact, hotspots and uncertainty | Factor packages with pinned versions (EF datasets, or ecoinvent under licence [ecoinvent]); contributions; Monte Carlo (4) | Unlicensed datasets unavailable, never substituted | MFG-O-SUST-2 | 3, 4 |
| Recyclability and repairability | Recoverable mass per stream from the disassembly graph; contaminating joints; access to service parts | Unlisted materials unrecoverable; `Unreachable` | MFG-O-SUST-3 | 3 |
| Passport mapping and identifiers | Delegated-act elements mapped to queries; identifiers per model, batch or item; carriers; public, professional and authority views | Unmapped elements block publication | MFG-O-DPP-1 | 3 |
| Registration and back-up copy | Registration through the Commission's API inside `publish_passport`, keeping the proof; each passport mirrored to the independent provider | Rejections typed; fails unless both copies succeed | MFG-O-DPP-2 | 3 |
| Battery passport | Battery Regulation elements for GP6's pack, required from 18 February 2027 for LMT, industrial above 2 kWh and EV batteries [EU Battery Regulation] | As mapping | MFG-O-DPP-1 | 4 |
| RoHS, REACH and SCIP | Ten RoHS substances at 0.1%, cadmium 0.01%, per homogeneous material [EU RoHS; EU 2015/863], from COV's declared substances (2); Candidate List, Annex XVII and SCIP data (3); IPC-1752C declarations [IPC store] | Unknown content reported as unknown, never compliant | MFG-O-REG-1 | 2, 3 |
| 3TG sourcing data | Smelter lists and due-diligence evidence collected for reporting | Data-completeness check only | MFG-O-REG-2 | 3 |
| Other regimes | Packaging, batteries, WEEE [EU WEEE], TSCA [EPA TSCA] and Proposition 65 as regulation packages | As RoHS | MFG-O-REG-1 | 4 |

## State of the art

All numeric goals in the last column are targets.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Adaptive clearing | Constant engagement; varied trochoids [Li et al. 2025] | Mastercam Dynamic Motion [Mastercam]; Fusion 3D Adaptive Roughing [Fusion adaptive]; hyperMILL [hyperMILL]; NX CAM [NX CAM] | Medial-axis spiral on stock (D-MFG-7) | Cycle time within 3% of the best at equal engagement; zero bound violations |
| 3-axis finishing | Drop- and push-cutter [OpenCAMLib] | ModuleWorks 3-axis [ModuleWorks] | `tool_contact` on exact B-rep | Scallop and gouge error on analytic surfaces; throughput at least OpenCAMLib's |
| Collision and NC verification | Continuous collision detection on posted code | ModuleWorks 5-axis [ModuleWorks]; VERICUT [VERICUT] | Posted text under declared semantics (D-MFG-23); certified gouge distance | Zero false negatives per family; time per 1,000 blocks |
| Material removal | Adaptive GPU tri-dexel [Ozcan et al. 2024] | ModuleWorks; VERICUT | Narrow-band stock (D-MFG-6) | Volume error against exact Booleans; 60 fps scrubbing of 10⁶ blocks |
| Feeds and speeds | Mechanistic force models with constrained optimization | CloudNC [CloudNC CAM Assist]; VERICUT Force [VERICUT Force] | D-MFG-27 | Cycle time within 5% of the leader, zero violations |
| Chatter | Zero-order, multi-frequency, semi-discretization [Altintas et al. 2008] | CUTPRO [Altintas et al. 2008] | Zero-order at `Interactive`, semi-discretization at `SignOff` (D-MFG-10) | Published lobes; time-domain reference |
| Posts | Configurable controller posts | NX Post Configurator, ModuleWorks posts [ModuleWorks] | One engine with Ingot hooks, restart points and qualification (D-MFG-5, D-MFG-31) | Re-interpretation; conformance and qualification corpora |
| Target recognition | Panoptic graph segmentation on B-rep [FeatureFox] | AAGNet [FeatureFox; AAGNet] | Design semantics, then rule and learned recognizers (D-MFG-34) | MFInstSeg panoptic quality at least 97%; above 0.9 with 250 parts |
| AI-assisted programming | Proposals with human review | CloudNC; NX suggestions [Janus NX 2606] | D-MFG-4 | Unedited approvals on held-out parts; zero bypasses |
| 2D nesting | Sparrow [Gardeyn et al. 2025] | Sparrow, jagua-rs [sparrow; jagua-rs] | Adopt with deterministic budgets (D-MFG-9) | Within 1 point of sparrow's density at equal wall-clock time |
| 3D packing | Interlock-free spectral packing [Cui et al. 2023] | Netfabb [Cui et al. 2023]; Magics [Materialise Magics] | Integer counts (D-MFG-12) | Thingi10K: within 2 points at equal GPU time |
| Slicing | Direct slicing; variable-width beads [Kuipers et al. 2020]; tree supports [OrcaSlicer] | OrcaSlicer, PrusaSlicer | Hand-off first (D-MFG-25); direct slicing (D-MFG-11) | Thin-wall fill and print time no worse; 10× less memory on lattices |
| Multi-axis slicing | Quaternion-field curved layers [Zhang et al. 2022] | The paper's BSD-3-Clause code [S3-Slicer code] | Adopt in phase 4 | Support-free coverage and collision-free order on the paper's models |
| Lattices | Implicit, Field-driven lattices | nTop [nTop] | MEC lattices checked and written without meshing | Relative density error under 1% |
| PBF distortion | Inherent strain set from coupons [Setien et al. 2019] | Magics with Ansys [Materialise Magics]; Fusion [Fusion Manufacturing Extension] | FLX's declared sequence; D-MFG-13 | AM-Bench bridge deflection within 10% [NIST AM-Bench 2018; NIST AM-Bench 2025]; GP2 within 0.1 mm |
| Injection molding | 3D non-isothermal flow; ARD-RSC [Phelps and Tucker 2009; Wang et al. 2008] | Moldflow [Moldflow] | 3D at `SignOff`, Hele-Shaw at `Interactive` (D-MFG-15, D-MFG-29) | Bay and Tucker's disk [Bay and Tucker 1992]; GP5 warpage within 20% |
| Casting | Filling, solidification, dimensionless Niyama [Carlson and Beckermann 2009] | MAGMASOFT [MAGMASOFT] | COV's solidification package, calibrated alloys only | WCB plate porosity; Stefan problem |
| Sheet forming | Incremental shell FEM with compensation | AutoForm [AutoForm] | Flux shells, Field-driven compensation | NUMISHEET 2014 springback benchmark [NUMISHEET 2014] |
| Weld distortion | Inherent strain [Murakawa et al. 2010]; moving-source transient [Goldak et al. 1984] | SYSWELD [SYSWELD] | Both by envelope; joint loads on beams (D-MFG-32) | GP4 distortion in band; NeT TG1 plate [NeT TG1] |
| Assembly planning | Assembly by disassembly [Tian et al. 2022] | Same (research) | Adopt with deterministic search (D-MFG-17) | Paper's benchmark; 80 parts under 5 minutes |
| Line balancing | BB&R [BB&R] | BB&R | Adopt | All 269 instances optimal, mean under 1 s |
| Robot offline programming | Redundancy-resolved collision-free planning | RoboDK [RoboDK]; Process Simulate [Process Simulate] | Robots as Machines sharing CAM kinematics and posts | Re-interpreted motion; cycle time within 10% |
| Inspection | Model-based QIF plans [ISO 23952]; GUM and JCGM 101 [BIPM JCGM] | ZEISS CALYPSO [CALYPSO]; PolyWorks Inspector [PolyWorks] | Provenance identities, stable balloons, uncertainty-aware decisions | QIF round trip; JCGM examples reproduced |
| Should-cost | Process-model cost from CAD [aPriori] | aPriori | Cost from generated plans, basis labelled (D-MFG-19) | Held-out quotes inside the interval for 90% of parts |
| Machine connectivity | MTConnect 2.5 [MTConnect 2.5]; OPC 40501-1 [OPC 40501-1] | MTConnect C++ reference agent [cppagent] | Read adapters, allowlisted job management, signed inputs (D-MFG-20) | Conformance against reference agents and servers |
| PCB handoff | IPC-2581C with DFX [IPC-2581C]; Gerber 2026.05 [Ucamco Gerber downloads] | Valor NPI [Valor NPI] | D-MFG-16 | 1 µm XOR against independent readers; seeded-defect boards |
| Life-cycle assessment | ISO 14040 and 14044 process LCA [ISO 14044] | openLCA [openLCA]; SimaPro [SimaPro] | Inventory from actual process plans | Mass balance; reference product systems |

## Platform notes

- **Identical features.** Strategies, nesting, slicing and simulations are Wasm components or core Rust, so every platform runs the same code.
- **Determinism.** Programs, nests and slice contours are canonical results, so NC text is identical on every Tier 1 platform. `correlate_grids` is `Certified` with exact integer counts, and the GPU tri-dexel cache only renders.
- **Browser memory.** Stock grids, voxel grids and large nests stream in tiles. Evaluations above PLT's thresholds move to the heavy worker or a server, and the UI says so.
- **Machine access.** Devices are reached through the gateway, since Web Serial is not Baseline [MDN Web Serial]. MTConnect, OPC UA and DNC never run inside evaluation.
- **Controller files.** Line endings, character sets, lengths, sizes, names and storage normalizations belong to the `Controller` record; the platform layer writes posted bytes unchanged.
- **Air-gapped shops.** Machine, tool, printer, material and regulation packages install offline through KLN's bundles (phase 3); results state the date of every External input.
- **Tier 2.** Tablets (PLT's phase 3) view programs, simulations and results and approve physical-effect Acts; phones only view (contract 7.6).
- **Licensing.** PrusaSlicer, OrcaSlicer, CuraEngine, libbgcode, KiCad and OpenCAMLib are external references only. Sparrow, cavalier_contours, i_overlay and Manifold are permissive, Clipper2 is BSL-1.0 [cavalier_contours; i_overlay; Manifold; Clipper2], and jagua-rs and async-opcua are MPL-2.0 under contract 7.7.

## Interfaces with other subsystems

### What MFG consumes

| From | Canonical name or type | Used for |
| --- | --- | --- |
| Anvil | `section`, `offset_curve`, `medial_axis`, `tool_contact`, `swept_volume`, `distance`, `interference`, `deform`, `split`, `extend`, `visibility`, `draft_map`, `thickness`, `voxelize`, `correlate_grids`, `align`, `fit`, `boolean`; wire and `Implicit` Bodies | Every planning capability |
| Flux | Modal analysis; `mark_reduction`; the inherent-strain sequence; thermo-elasto-plasticity; level-set flow and Hele-Shaw; shells, contact, sensitivities; topology optimization | Process physics |
| COV | Material models and envelopes (D-MFG-30); strut-scale Materials; Hele-Shaw, strut and Weber regime variables; OOR-8; `EnvironmentalRecord`s; gear, bearing and shaft ratings | Envelope checks; LCA |
| MEC | Kinematic mates; flat patterns; `HoleSpec`, `ThreadSpec`, `Weld` with quality level and execution class; general tolerances; gear records; `split_mold`; `lattice`; PMI and balloons; fallback regions; harness geometry | Planning, inspection |
| ELX | Board model with classes, netlist, placements, `test_point` features, via classes and coating record; the DRC engine; harness data | Board and harness handoff |
| KLN and `repo` | `ItemDefinition` per kind, effectivity, BOM views, MCOs (D-KLN-38), Waivers, recipient records, Evidence records and watermark, the limit catalog | Release, FAI, as-built |
| AGT and `api` | Acts, Approvals and the approval page; `read.machine_data`; Proposals; CAM programmer and cost engineer roles (phase 2) | Transfers, agent work |
| ECO | `io/` readers and writers (3MF, IPC-2581, Gerber, IPC-D-356, ODB++, QIF, STEP-NC, USD, ISO 13399); `parts::` and offers; `erp-connector` and `mes-connector` (phase 2) | Outputs and imports |
| UIX, PLT, ING | Manufacture preset; gateway packaging, device keys and the reference laptop; records, `Money<C>`, `round_minor` and `require` | Review, connectivity, Ingot |

### What MFG provides

| To | Provided | Type |
| --- | --- | --- |
| All tabs | `std::mfg` packages: `core`, `machining`, `am`, `molding`, `casting`, `forming`, `joining`, `treatment`, `electronics`, `assembly`, `inspection`, `cost`, `sourcing`, `factory`, `sustainability` | Ingot packages |
| MEC | Process profiles (Cp, Cpk, accepted representations), press-brake allowance data, cost models, characteristic identities and labels, the harness package, DFM, DFA and DfAM checks | `Check`, `Field`, packages |
| FLX and COV | Process profiles for manufacturing-constraint forms; coupon data for inherent strain, weld joints and as-built struts; process data under D-MFG-30 | `Field`, packages |
| ELX | Rule packs by class; package choice; panels, stencils, test programs; DFX feedback | `Check`, packages |
| KLN and `repo` | Program subjects and `ItemDefinition`s with simulation evidence; first-article records; MBOM and routings; setup sheets, instructions and inspection plans; as-built records | CAS objects |
| AGT | Typed physical-effect payloads with the approval page's fields; `request_quote` and `publish_passport` payloads; `MfgError` fixes | Act plans |
| UIX | Toolpaths, stock, collisions, NC text with `BlockMap` and compensation modes, setup sheets, DfAM and carbon Fields, cost lines | `Body`, `Field` |
| ECO | `verify_nc`; `crucible:mfg` worlds (`toolpath-strategy`, `post-processor`, nesting, packing, slicers, recognizers); connector manifests with endpoint allowlists | WIT interfaces, packages |
| PLT | `apps/machine-gateway` for packaging | App |

## Oracles

Oracles live in `oracles/mfg/`, which agents read but never write; held-out parts, programs, nests and measurements are never shown to agents. Loosening a tolerance below needs a human Approval.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| MFG-O-CORE-1 | Records and fixes | Every artifact is a Body, Field, Assembly or plain value; every seeded failure carries a fix that clears it or says why not |
| MFG-O-CORE-2 | Outside data | Every External input and Evidence record read appears by `ObjectId` in its `CheckOutcome` |
| MFG-O-CORE-3 | Toolpath storage | 10⁷ moves under 400 MB (target); single moves addressable |
| MFG-O-CORE-4 | Representations | Seeded fallback regions release only for accepting processes or after conversion in tolerance; PMI on one fails |
| MFG-O-DET-1 | Determinism | Identical programs, nests, builds and reports on every Tier 1 target; "continue" never worsens a result |
| MFG-O-LABEL-1 | Label invariance | GP1 to GP3 plans and costs identical after re-randomizing every name |
| MFG-O-SAFE-1 | Subjects and changes | Edits inside a subject void Approvals, rebases and pocket changes do not; MCOs touching EBOM definitions rejected; a part change returns exactly its dependent programs, legacy ones included |
| MFG-O-SAFE-2 | Transfers and starts | Unapproved, forged, mismatched, phone-approved and unconfirmed requests refused 100%; `start_print` refuses profile-only declarations, non-extrusion printers and remote confirmations; programs survive simulator round trips, single-token edits never do |
| MFG-O-SAFE-3 | No start on the wire | Under wire capture against real servers or simulators (OctoPrint, Moonraker, PrusaLink, URSim, controls), no request carries a start or non-allowlisted method, and devices stay idle |
| MFG-O-SAFE-4 | Offsets and edits | Seeded offset mismatches blocked 100%; post-transfer edits alarm within 5 s; edit sessions yield exact diffs |
| MFG-O-SAFE-5 | DNC | Every injected feed fault stops and reports; controls waiting for data at commit receive zero bytes in 100% of cases |
| MFG-O-SAFE-6 | Program registry | Seeded collisions with foreign programs refused 100%; later revisions of the same Item replace their slot |
| MFG-O-KIN-1 | Kinematics | `fk` against a screw-theory implementation on 10,000 poses under 10⁻¹² m; `fk(ik(p))` equals `p` within 10⁻⁹ |
| MFG-O-KIN-2 | Singularities and limits | No unreported branch flip; tip deviation, axis derivatives, power and torque under bounds |
| MFG-O-POST-1 | Posts | An independent interpreter reproduces each program; family corpora match vendor simulators and reference-shop controls |
| MFG-O-POST-2 | Hooks | Golden posted files per configuration and hook set |
| MFG-O-POST-3 | Qualification | Reference programs equal the shop's proven ones modulo the declared list; captured corpus traces match `MotionSemantics` within tolerance |
| MFG-O-POST-4 | Diff and block map | Self-diff empty; known edits found; every block maps to a toolpath point |
| MFG-O-TOOL-1 | Tools | Package round trip within 1 µm; gauge length equals the analytic stack-up; conflicting entries fail |
| MFG-O-TOOL-2 | Tool life | Predicted changes within ±25% of as-run counts (target) |
| MFG-O-STOCK-1 | Stock | Removed volume equals swept volume within the bound; rest plus part covers stock; exact hand-off transforms |
| MFG-O-SETUP-1 | Setup sheets | Tombstone corpus verified per offset; offsets, program number, restart points and every tool appear once |
| MFG-O-SETUP-2 | Jaws and probing | Parts seat without interference; probe paths collision-free |
| MFG-O-SETUP-3 | Fixtures | Rank tests on 3-2-1 cases; equilibrium and deflection in tolerance; access clear |
| MFG-O-MILL-1 | 2.5D and rest | No material above floor plus allowance; rest Body empty after the pass |
| MFG-O-MILL-2 | Engagement | An independent stock simulator keeps engagement and chip thickness under bound plus tolerance |
| MFG-O-MILL-3 | Finishing | Scallop Field under target; certified gouge check passes |
| MFG-O-MILL-4 | Edges, threads, holes | Chamfer size, thread profile, hole depth and position on simulated stock |
| MFG-O-MILL-5 | 5-axis | Wall deviation in tolerance; collision passes; axis smoothness bounds hold |
| MFG-O-TURN-1 | Turning | Revolved profile equals the part; simulated profile within allowance |
| MFG-O-TURN-2 | Multi-channel | Collision-free schedules honoring synchronization; optimal on small instances |
| MFG-O-EDM-1 | EDM | Kerf and ruled surfaces in tolerance; electrode plus gap reproduces the cavity |
| MFG-O-GEAR-1 | Gear cutting | Simulated flanks within the ISO 1328-1 grade on MEC's record; ground profiles within allowance |
| MFG-O-GEAR-2 | Gear inspection | Plans evaluate the design flank on reference gears |
| MFG-O-CUT-1 | Profile cutting | Kerf, taper, bevel and punched sheet match the part; tour against a lower bound; the generic post reproduces the paths |
| MFG-O-CUT-2 | Flat-pattern hand-off | Every entity mapped per convention; re-import equals the flat pattern |
| MFG-O-CUT-3 | Press brake | Bends collision-free; optimal on small instances; bend-sheet values equal the plan |
| MFG-O-NEST-1 | Nests | Exact overlap and containment checks; remnant plus parts plus kerf equals the sheet; warm starts never worsen; ESICUP density within 1 point of sparrow at equal wall-clock time on the reference laptop |
| MFG-O-FEED-1 | Cutting data | Labels match sources; coefficients reproduce calibration cuts within uncertainty |
| MFG-O-FEED-2 | Constraint check | Spindle power within 10% of spindle-load data (target); no missed violation on recomputation |
| MFG-O-FEED-3 | Optimization | Zero violations; cycle time within 5% of the leader |
| MFG-O-CHAT-1 | Stability | Published FRFs and lobes; time-domain agreement; recorded chatter flagged |
| MFG-O-SIM-1 | Gouges | Every planted gouge found with its depth, including wear values outside `wear_range` |
| MFG-O-SIM-2 | Collision | Ordinary and controller-semantics crash corpora detected 100% per family; undeclared semantics never pass |
| MFG-O-SIM-3 | External NC | Hand-written, third-party, macro-calling and probe-branching programs with planted crashes detected or `Undecided`, never passed |
| MFG-O-SIM-4 | Cycle time | Within 5% of measured after calibration (target) |
| MFG-O-SIM-5 | Viewer | Visual regression Snapshots under a fixed `RenderProfile` |
| MFG-O-SIM-6 | Restarts | Every restart entry collision-free; seeded restarts that skip the restatement caught |
| MFG-O-PROG-1 | Regeneration | Unchanged designs keep every `ObjectId`; identical programs diff empty |
| MFG-O-PROG-2 | Templates and setups | Golden programs for template parts; deterministic ranking; each target in one setup |
| MFG-O-PROG-3 | Recognition | Panoptic quality targets on MFInstSeg; training data licensed for commercial use |
| MFG-O-PROG-4 | Agent programs | Held-out agent Proposals pass every oracle; zero bypasses |
| MFG-O-PROG-5 | STEP-NC | Schema validation; round trips exact or within AP242 tolerance |
| MFG-O-AM-1 | Orientation | Objectives recomputed; brute force on small grids |
| MFG-O-AM-2 | Build hand-off | Named slicers and the bureau's software open the 3MF intact; GP2's mesh export meets its targets |
| MFG-O-AM-3 | Packing | Exact clearance and translational removability |
| MFG-O-AM-4 | Supports and labels | Every overhang and island supported; removal access; labels legible on layers |
| MFG-O-AM-5 | DfAM and lattices | Seeded-defect corpus: every defect found, no clean region flagged |
| MFG-O-AM-6 | Slices | Layer area equals cross-section within the bound; contours closed; bead fill ratio; DED deposition |
| MFG-O-AM-7 | Distortion | Coupon deflection within its uncertainty; AM-Bench 2018 bridge deflection within 10% (target) |
| MFG-O-AM-8 | Compensation | Re-simulated build in tolerance; a compensated metal PBF build of GP2's geometry within 0.1 mm in phase 2 (target) |
| MFG-O-AM-9 | Cure, sintering, warp | AM-Bench cure depth; measured shrinkage and warp coupons |
| MFG-O-AM-10 | 3MF | Consortium validation and round trip |
| MFG-O-AM-11 | Printer data | bgcode decodes to the same moves with an independent reader; calibration prints reproduce recorded values |
| MFG-O-AM-12 | Strut calibration | Held-out coupons fall within the stated uncertainty; strut-scale Materials cover every GP2 strut diameter and angle |
| MFG-O-MOLD-1 | Moldability and split | Analytic draft; seeded undercuts; core plus cavity plus part equals the block |
| MFG-O-MOLD-2 | Mold design | Opening collision-free; pin stress, fill imbalance and steel distance in limits; turbulent coolant |
| MFG-O-MOLD-3 | Flow | Center-gated disk and power-law Hele-Shaw solutions; mass within 0.1%; thresholds calibrated on the step plate and ribbed plaque |
| MFG-O-MOLD-4 | Orientation and warpage | a₁₁ within 0.1 on Bay and Tucker's centre-gated disk; GP5 warpage within 20% (targets) |
| MFG-O-CAST-1 | Casting design | Pattern minus allowances equals the part; velocities and moduli recomputed |
| MFG-O-CAST-2 | Casting simulation | Stefan problem; energy balance per cycle; WCB plate porosity |
| MFG-O-BULK-1 | Bulk forming | Forging load within 10% and die fill matching the phase 5 partner's measured parts (target) |
| MFG-O-FORM-1 | Tube bending | Collision-free simulation; measured tubes |
| MFG-O-FORM-2 | Forming | NUMISHEET 2014 Benchmark 2 springback within 1° (target); tonnage recomputed |
| MFG-O-JOIN-1 | Weld procedures | Every joint has a qualified procedure, quality level and execution class; pass areas sum to the joint |
| MFG-O-JOIN-2 | Weld distortion | GP4 distortion in the prediction band; coupons within their uncertainty; NeT TG1 residual stress within 50 MPa in phase 4 (target) |
| MFG-O-JOIN-3 | Fastening and bonding | Preload range contains MEC's requirement; pitch, edge and access rules; bead volume equals bondline |
| MFG-O-JOIN-4 | Composites | Every ply placed once in order; gaps and overlaps in limits; spring-in on L-sections |
| MFG-O-TREAT-1 | Coatings | Every treated face resolved; dimensions recomputed; plating cases and film thickness |
| MFG-O-TREAT-2 | Heat treatment | Hardness and case depth within COV bands; golden-part distortion within 20% of prediction or 0.05 mm (target) |
| MFG-O-PCB-1 | Fabrication packages | Every file the fabricator profile requires; independent readers and a 1 µm XOR against the board empty; writers are ECO-O-25 |
| MFG-O-PCB-2 | Assembly outputs | Placements from the 3D Assembly within 0.01 mm and 0.1° |
| MFG-O-PCB-3 | Classes and drawing | Each class selects its rule pack; notes equal board values |
| MFG-O-PCB-4 | Panels, stencils, reflow | Panel rules hold; area ratios recomputed; profile inside every part's rating |
| MFG-O-PCB-5 | DFM and DFA | Seeded-defect boards: every defect found |
| MFG-O-PCB-6 | Test | Coverage recomputed from the netlist; proposed points reach every accessible net |
| MFG-O-HARN-1 | Harness package | Cut list, terminals and test netlist match ELX connectivity; formboard lengths match MEC |
| MFG-O-ASM-1 | Sequences | Every motion replayed collision-free; optimum on small instances; each fastener in one step |
| MFG-O-ASM-2 | DFA | Known minimum part counts; times trace to table rows |
| MFG-O-ASM-3 | Instructions | Every MBOM item consumed; schema and accessibility checks; unchanged designs diff empty |
| MFG-O-ASM-4 | Robots | Replayed paths collision-free; posts reproduce motion; no safety-configuration output; loading paths pass MFG-O-SAFE-3 |
| MFG-O-ASM-5 | Line balancing | All 269 benchmark instances optimal; bounds reported |
| MFG-O-INSP-1 | Characteristics | One characteristic per control and general tolerance; a one-dimension revision changes one balloon and no labels; Form 3 equals the balloons |
| MFG-O-INSP-2 | Methods and CMM | Uncertainty ratios recomputed; paths collision-free on the CMM model |
| MFG-O-INSP-3 | Results | Public QIF samples and CSV templates round trip; one signed, pinned record per characteristic |
| MFG-O-INSP-4 | Evaluation and scans | Gaussian fits pass ISO 10360-6:2001's error estimation [ISO 10360-6]; known transforms recovered |
| MFG-O-INSP-5 | Uncertainty and decisions | JCGM worked examples reproduced; calibrated artifacts; seeded results at zone edges decided per D-MFG-33 |
| MFG-O-QUAL-1 | SPC, MSA, capability | Published chart, capability and gauge R&R examples reproduced exactly |
| MFG-O-QUAL-2 | FAI | Revision C fields complete; seeded changes give the expected partial scope; first-article records join every characteristic |
| MFG-O-QUAL-3 | PPAP and FMEA | Element completeness per level; every special characteristic controlled |
| MFG-O-COST-1 | Parametric cost | Held-out quotes inside the interval for 90% of parts (target) |
| MFG-O-COST-2 | Planned cost | Hand-computed reference parts per process |
| MFG-O-COST-3 | Roll-ups | Roll-up equals the sum; allocations sum to targets; currency mixing fails to compile |
| MFG-O-COST-4 | Quotes | Mock supplier endpoints; requests only inside Acts |
| MFG-O-SRC-1 | Suppliers | Signatures checked; seeded mismatches detected; alternates' checks pass |
| MFG-O-SRC-2 | Decisions and risk | Decisions recomputed from inputs; seeded risks surfaced |
| MFG-O-FAC-1 | Gateway | Offline replay; TPM-signed records; readings without a TPM marked `data_untrusted`; no inbound port |
| MFG-O-FAC-2 | Adapters | Reference agents and servers with recorded streams; sessions below `SIGNANDENCRYPT` refused |
| MFG-O-FAC-3 | MES and ERP | Mock-endpoint round trip with idempotent replay |
| MFG-O-FAC-4 | MBOM and routings | Every EBOM item consumed once; times trace to programs; one routing per serial |
| MFG-O-FAC-5 | USD and twin export | Core 1.0 validation; transforms and animation in tolerance |
| MFG-O-FAC-6 | As-built | Complete genealogy for test serials |
| MFG-O-FAC-7 | Calibration | Updated models predict held-out runs better, otherwise rejected |
| MFG-O-SUST-1 | Carbon and inventory | Roll-up equals the sum; mass balance per routing step |
| MFG-O-SUST-2 | Impact | Reference product systems; contributions sum to the total |
| MFG-O-SUST-3 | Circularity | Streams plus losses equal product mass; paths replayed |
| MFG-O-DPP-1 | Passport mapping | Every element mapped or justified as not applicable; carriers decode |
| MFG-O-DPP-2 | Publication | Test-registry round trip; back-up copy at the second provider |
| MFG-O-REG-1 | Restricted substances | Seeded BOMs: every planted case reported with part, material and rule |
| MFG-O-REG-2 | 3TG data | Missing evidence reported; no compliance verdict |
| MFG-O-GOLD-1 | Golden products | GP1 and GP2 costs, DfAM verdicts and conformance decisions; GP2 strut calibration; GP3 parts from Crucible programs; GP4 distortion; GP5 warpage and board; GP6 build records and passport |

## Phasing

MFG-O-GOLD-1 collects the gate evidence below. Shared capabilities take their phase from contract 13.4, which the capability tables follow; press-brake allowance data and metal PBF compensation keep MFG's phase 2.

| Phase | MFG contribution to the gate |
| --- | --- |
| 0 | Core types, `MfgError`, seeded search rules and the protected oracle directory |
| 1 | GP1: coating specification, parametric cost, BOM roll-up and conformance decisions on characteristics; the shop's own CAM. GP2: DfAM and lattice checks, strut calibration, orientation, 3MF to the bureau, AM cost; no distortion prediction. CAM, posts, simulation, slicing and nesting wait (contract 13.2) |
| 2 | GP3: CAM for housings, shafts and blanks; gear inspection plans; four post families with restart points; posted-code simulation and `verify_nc`; the gateway with transfer Acts, registry, offset watch and pull-only DNC; first-article records. GP4: profile cutting, nesting, bend sheets, weld procedures and distortion. One material-extrusion part through Crucible's slicer. Also inherent-strain data, PBF compensation and ERP and MES mapping |
| 3 | GP5: mold design, fill, orientation and warpage; board packages; CMM programs, SPC, MSA and AS9102. Also 5-axis, stability lobes, native bend programs, MTConnect and OPC UA reads, passports |
| 4 | GP6: harness package, layup and battery passport. Also gear generating, PBF scan vectors, joint-scale weld simulation, PBF thermo-mechanics, PPAP and MES feedback |
| 5 and later | Sheet forming, springback, plating current, bulk forming and GP8's execution class (5); casting simulation and heat-treatment distortion (6) |

## Open questions

1. **Freedom to operate.** Does an engagement-controlled spiral without a pre-roughing slot avoid US 9,164,503 and the other engagement-control families? It stays open until counsel's opinion, which gates adaptive clearing.
2. **GP2's build-preparation software.** The phase 0 gate fixes the bureau's software and its accepted 3MF extensions (contract 13.1). Until then D-MFG-25 keeps both the Beam Lattice and the mesh file.
3. **Findings applied in part in round 3.**
   - R8-44's "machining with mesh-capable CAM" is declined: STEP processes accept B-rep only, which shops' CAM and CMM read (R10-37).
   - R12-11's polymer branch lapses: contract 13.1 fixes GP2 as metal laser powder bed fusion. Its calibration build is the strut coupons in contract 13.2's chain B.
   - R10-29's capture time in the reference-shop agreement is CCR-MFG-7.
   - R10-01's and R10-43's robot loading paths are machine-package data, so the tab names only the documented ones.
   - R7-09's GP5 cell count is an estimate over an assumed cavity area until GP5's design exists.
   - R10-18 and R10-25: ratings, gear data tables and board spacing are COV's, MEC's and ELX's; MFG applies their inspection and test-access consequences.
4. **Earlier rounds.** Round 2's partly applied and declined findings are recorded in the Adversarial review tab.

## Contract change requests

- CCR-MFG-7, controller capture: contract 13.2's reference-shop agreement adds time on each family's physical controls in program-test mode (R10-29). Without it no post family can qualify.
- Earlier: CCR-MFG-5 and CCR-MFG-6 were accepted in contract v5, and the machine gateway request in v6 (contract 12).

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
- [Haas G-codes] Haas mill G-codes G00, G234, G268, G187, G81 and G89: https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G00.html , https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G234.html , https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G268.html , https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G187.html and https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G81.html
- [Haas operation] Haas mill operator's manual, operation and macros: https://www.haascnc.com/service/online-operator-s-manuals/mill-operator-s-manual/mill---operation.html and https://www.haascnc.com/service/online-operator-s-manuals/mill-operator-s-manual/mill---macros.html
- [Heidenhain TNC] https://www.klartext-portal.com/tips/nc-solutions/alignment-with-plane-function , https://www.klartext-portal.com/tips/programming/cycle-32-tolerance and https://content.heidenhain.de/doku/tnc_guide/pdf_files/TNC620/81760x-03/zyklen/1096886-22.pdf
- [Siemens Sinumerik] https://cache.industry.siemens.com/dl/files/454/37335454/att_110322/v1/SIN_WF5_0509_en.pdf and https://cache.industry.siemens.com/dl/files/376/24763376/att_80970/v1/PGZ_0108_en_en-US.pdf
- [Fanuc CNC] https://www.fanucamerica.com/products/cnc/5-axis-cnc-machining and https://www.fanucamerica.com/products/cnc/31i-b5
- [Sandvik Coromant tool data] https://sandvik.coromant.com/en-gb/tools/tool-data
- [Mitsubishi Materials] Mitsubishi Materials, ToolsUnited article: https://www.mmc-carbide.com/cz/download/magazine/vol10/cut_vol10
- [ISO 1328-1] ISO 1328-1:2013: https://www.iso.org/standard/45309.html
- [AAGNet] https://github.com/whjdark/AAGNet
- [OctoPrint files API] https://docs.octoprint.org/en/master/api/files.html
- [Moonraker file manager] https://moonraker.readthedocs.io/en/latest/external_api/file_manager/
- [PrusaLink OpenAPI] https://raw.githubusercontent.com/prusa3d/Prusa-Link-Web/master/spec/openapi.yaml
- [UR client interfaces] https://www.universal-robots.com/articles/ur/interface-communication/overview-of-client-interfaces/
- [Bambu Developer Mode] Bambu Lab, "Updates and third-party integration with Bambu Connect": https://blog.bambulab.com/updates-and-third-party-integration-with-bambu-connect/
- [3MF Beam Lattice] 3MF Beam Lattice Extension 1.2.0: https://raw.githubusercontent.com/3MFConsortium/spec_beamlattice/master/3MF%20Beam%20Lattice%20Extension.md
- [3MF Core] 3MF Core Specification 1.4.0, section 3.4: https://raw.githubusercontent.com/3MFConsortium/spec_core/master/3MF%20Core%20Specification.md
- [PrusaSlicer 3MF] https://help.prusa3d.com/article/saving-projects-as-3mf_1773
- [OrcaSlicer 3MF] https://github.com/OrcaSlicer/OrcaSlicer/wiki/publish_3mf and https://github.com/OrcaSlicer/OrcaSlicer/blob/main/src/libslic3r/Format/bbs_3mf.cpp
- [Bambu Studio CLI] https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage
- [Setien et al. 2019] Setien et al., "Empirical methodology to determine inherent strains in additive manufacturing", Computers & Mathematics with Applications 78(7): https://upcommons.upc.edu/handle/2117/132354
- [Phelps and Tucker 2009] J. Non-Newtonian Fluid Mech. 156(3), 165–176, doi 10.1016/j.jnnfm.2008.08.002: https://api.crossref.org/works/10.1016/j.jnnfm.2008.08.002
- [Wang et al. 2008] Wang, O'Gara, Tucker, J. Rheol. 52(5), 1179–1200, doi 10.1122/1.2946437: https://api.crossref.org/works/10.1122/1.2946437
- [Bay and Tucker 1992] "Fiber orientation in simple injection moldings. Part II: Experimental results", Polymer Composites 13(4), 332–341: https://api.crossref.org/works/10.1002/pc.750130410
- [NIST AM-Bench 2018] AMB2018-01 bridge structures: https://www.nist.gov/ambench/amb2018-01-description
- [NeT TG1] Smith, Smith, Wimpory, Ohms, NeT TG1 single bead on plate, IJPVP 120–121 (2014): https://publications.jrc.ec.europa.eu/repository/handle/JRC91654
- [NUMISHEET 2014] Benchmark 2, springback of a draw/re-draw panel, AIP Conf. Proc., doi 10.1063/1.4849980: https://api.crossref.org/works/10.1063/1.4849980
- [Goldak et al. 1984] Goldak, Chakravarti, Bibby, Metall. Trans. B 15, 299–305: https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/BF02667333
- [Murakawa et al. 2010] Murakawa, Deng, Ma, Trans. JWRI 39(2), 103–105: https://ir.library.osaka-u.ac.jp/repo/ouka/all/5063/jwri39_02_103.pdf
- [S3-Slicer code] https://github.com/zhangty019/S3_DeformFDM
- [nTop] https://www.ntop.com/platform/ and https://www.ntop.com/resources/blog/user-spotlight-yamaha-pairing-topology-optimization-with-graded-lattices/
- [SYSWELD] https://www.keysight.com/us/en/products/design-engineering-software/computer-aided-engineering-software/welding.html
- [Mastercam] https://www.mastercam.com/solutions/
- [Fusion adaptive] https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/3D-ADAPTIVE-READ.htm
- [hyperMILL] https://www.openmind-tech.com/en/
- [NX CAM] https://www.siemens.com/en-us/products/nx-manufacturing/cam-software/
- [VERICUT] https://vericut.com/products
- [VERICUT Force] https://vericut.com/products/force-optimization
- [RoboDK] https://robodk.com/offline-programming
- [RoboDK post processors] https://robodk.com/doc/en/Post-Processors.html
- [RoboDK KUKA] https://robodk.com/doc/en/Robots-KUKA.html
- [RoboDK UR] https://robodk.com/doc/en/Robots-Universal-Robots.html
- [RoboDK Fanuc] https://robodk.com/doc/en/Robots-Fanuc.html
- [Process Simulate] https://www.siemens.com/en-us/products/tecnomatix/process-simulate-software/
- [CALYPSO] https://www.zeiss.com/metrology/en/software/zeiss-calypso.html
- [PolyWorks] https://www.polyworks.com/en-us/products/polyworks-inspector
- [cppagent] MTConnect C++ reference agent, Apache-2.0: https://github.com/mtconnect/cppagent
- [Valor NPI] https://www.siemens.com/en-us/products/pcb/valor/valor-npi/
- [openLCA] https://www.openlca.org/
- [SimaPro] https://simapro.com/
- [ecoinvent] https://ecoinvent.org/
- [EVS ISO 10218-1] ISO 10218-1:2025: https://www.evs.ee/en/iso-10218-1-2025
- [EVS ISO 10218-2] ISO 10218-2:2025: https://www.evs.ee/en/iso-10218-2-2025
- [EVS EN 1090-2] EN 1090-2:2018+A1:2024: https://www.evs.ee/en/evs-en-1090-2-2018-a1-2024-consolidated
- [IPC store] IPC current revisions (IPC-6012F, IPC-A-600M, IPC-A-610J, J-STD-001J, IPC/WHMA-A-620F, IPC-4761, IPC-D-356B, IPC-1752C): https://shop.electronics.org
- [Boothroyd et al. 2011] Boothroyd, Dewhurst, Knight, Product Design for Manufacture and Assembly, 3rd ed.: https://www.routledge.com/Product-Design-for-Manufacture-and-Assembly/Boothroyd-Dewhurst-Knight/p/book/9781420089271
- [DFMA DFA] https://www.dfma.com/software/dfa.asp
- [ISO 22093] ISO 22093:2011 (DMIS): https://www.iso.org/standard/56444.html
- [ISO 14253-1] ISO 14253-1:2017: https://www.iso.org/standard/70137.html
- [ISO 10360-6] ISO 10360-6:2001: https://www.iso.org/standard/28095.html
- [ISO 14040] ISO 14040:2006 with Amd 1:2020: https://www.iso.org/standard/37456.html
- [IEC 62443-3-3] IEC 62443-3-3:2013: https://webstore.iec.ch/en/publication/7033
- [OPC UA Part 4] OPC UA Part 4, MessageSecurityMode: https://reference.opcfoundation.org/Core/Part4/v105/docs/7.20
- [EU Battery Regulation] Regulation (EU) 2023/1542: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R1542
- [EU 2015/863] Commission Delegated Directive (EU) 2015/863: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32015L0863
- [EU WEEE] https://environment.ec.europa.eu/topics/waste-and-recycling/waste-electrical-and-electronic-equipment-weee_en
- [EPA TSCA] https://www.epa.gov/laws-regulations/summary-toxic-substances-control-act

- [EVS welding] ISO 15609-1:2019, ISO 15614-1:2017 with Amd 1:2019 and ISO 9606-1:2012: https://www.evs.ee/en/iso-15609-1-2019 , https://www.evs.ee/en/iso-15614-1-2017 and https://www.evs.ee/en/iso-9606-1-2012
