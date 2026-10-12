# Manufacturing (MFG)

Manufacturing is the part of Crucible that turns a released design into made parts: `std::mfg` plans machining, printing, moulding, welding, inspection, cost and factory records as one typed plan that regenerates when the design changes. Where a CAM file, a verification run and an inspection plan each keep their own copy of the part, here a design change re-plans exactly the operations it touches and re-checks the posted program, the G-code the machine reads, on a model of the real controller. A named person approves the digest of each program with its setup sheet and simulation results, the machine gateway on the shop floor refuses anything else, and a person at the machine starts every cycle.

## From model to machine

This section follows one part from its Ingot model to a running machine, because every later section adds detail to one step of this path.

### A worked example: machining the bracket

The example is the canonical bracket of contract section 6: a 6061-T6 plate 60 mm by 40 mm and 6 mm thick, with a 20 mm web standing on its top edge and 2 mm fillets. In phase 2 Crucible programs it for a 3-axis vertical machining centre, the way it programs GP3's housings and shafts. In phase 1, GP1 is still cut by the reference shop's own CAM from Crucible's STEP AP242 file, and MFG contributes its coating specification, its cost and the conformance decisions on its measurements (contract 13.1).

```
use std::mfg::{stock, setup, vise, soft_jaws, program, face, offset_clearing, finish_walls, chamfer_edges, cycle_time}
use std::materials::alu_6061_t6
use shop::machines::vf2
use shop::tools::{fm_50, em_10_3fl, em_6_4fl, chamfer_90}

pub fn bracket_program(p: Part) -> Program {
    let blank = stock(kind: bar, material: alu_6061_t6, size: (65mm, 45mm, 32mm))
    let op1 = setup(machine: vf2, fixture: vise(jaw_width: 150mm), part: p, stock: blank, wcs: G54)
    let op2 = setup(machine: vf2, fixture: soft_jaws(fit: p), part: p, from: -z, stock: op1.output(), wcs: G55)
    let steps = [
        face(op1, tool: fm_50),
        offset_clearing(op1, op1.removal(), tool: em_10_3fl, max_engagement: 70deg, allowance: 0.3mm),
        finish_walls(op1, op1.walls(), tool: em_6_4fl, scallop: 2um),
        chamfer_edges(op1, p.edges(convex), tool: chamfer_90, size: 0.5mm),
        face(op2, tool: fm_50),
    ]
    program(setups: [op1, op2], steps: steps)
        .require(cycle_time(steps) < 15min, name: "bracket_cycle")
}
```

Read it as a machinist would plan the job.

1. **Stock and setups.** The blank is a saw-cut bar. Setup 1 holds it in a vise on the machine `vf2` with work offset G54 and cuts everything reachable from above. Setup 2 turns the part over (`from: -z`), grips the machined web in soft jaws and faces the plate to thickness. Its blank is setup 1's output stock, `op1.output()`, so the hand-off between setups is computed, never redrawn.
2. **Workingsteps.** Each entry of `steps` is a workingstep, ISO 14649's word for what shops call an operation: a target, a strategy with its tool, and the toolpath the strategy computes. Targets are queries. `op1.removal()` is the material between the blank and the part that the setup's tool axis can reach, and `op1.walls()` selects the part faces parallel to that axis. Nothing names a face by a number, so the plan survives the edits that keep the part's shape.
3. **Toolpaths.** Each strategy is a sandboxed Wasm component that returns a `Toolpath`: a wire Body whose edges are runs of one motion kind (cut, plunge, link, rapid), with feed, spindle speed and tool axis carried as Fields. The roughing pass uses engagement-limited offset clearing, which keeps the tool's engagement with the true remaining stock below 70°.
4. **Post and simulation.** The post engine writes the NC text for the machine's controller and a `BlockMap` that links every block to its workingstep and path position. Simulation then runs the posted text, not the toolpath, under the controller's declared motion semantics. It measures the certified distance between every tool move and the design surface (gouges), checks the tool, holder, vise and machine for collisions, and predicts the cycle time. The check `bracket_cycle` decides on that prediction like any other `require`.
5. **Review and approval.** The programmer, or an agent on a branch, opens a Proposal. The reviewer plays the toolpath against the stock, reads the setup sheet and the semantic NC diff, and approves the program subject on the approval page: the program digests, machine class, nominal tools, setup sheet, simulation verdicts and block map. A `send_to_machine` Act stores the program in the control through the machine gateway, which checks the Approval, the program number, the hash and the offsets actually loaded. A person at the machine starts the cycle.
6. **Prove-out and first article.** The first parts run in the program's `Prototype` state, usually inside a bench session that lets the machinist re-send corrected versions for a few hours under one Approval. Feed values the machinist edits in the program at the control come back as a Proposal on the program's branch. The first good part is measured, each characteristic's result returns as a signed Evidence record, and the first-article record moves the program to `Proven`. A manufacturing change order then releases it, and any qualified machine of its class may pull it.
7. **The design changes.** Someone thickens the plate from 6 mm to 8 mm. Kiln re-runs only the workingsteps whose targets changed: setup 2's facing pass and the roughing levels near the plate. A trim the programmer applied to an air-cutting pass survives, because it names the pass by its key, not by a move number. The review shows the toolpath difference painted on the part and the semantic NC diff. Because the program subject changed, the old Approval no longer covers it, and the program returns to `Prototype` for a new one.

What the engineer gains is that these seven steps are one model. In incumbent tools the toolpath is associative inside one CAM file, but verification is a separate product run on exported G-code. The control accepts whatever file it is given, and the inspection plan lives in a third tool keyed by balloon numbers.

An AI-built clone can generate plausible toolpaths quickly. What it cannot copy in weeks is the chain that makes them safe to run. That chain is crash corpora captured on physical controls per controller family, certified gouge distances, Approvals bound to content digests, and a gateway that refuses every program it was not shown.

### The model a user meets

Machines, fixtures, moulds, nests and panels are Assemblies; cutting tools, holders and probes are catalog parts. An industry "operation" is a workingstep, and a "manufacturing feature" is a machining target found by a `Query`. Everything else is an ordinary record over Bodies, Fields and Assemblies:

```
// std::mfg::core (illustrative; ING fixes record syntax)
pub record Toolpath {
    path:    Body,                        // wire Body: one edge per run of one motion kind
    passes:  Map<PassKey, [EntityId]>,    // the edges of each pass, in cutting order
    tool:    Instance,                    // tool Assembly in its holder
    axis:    Field<Body, Direction>,
    feed:    Field<Body, Velocity>,
    spindle: Field<Body, AngularVelocity>,
    kinds:   Map<EntityId, MotionKind>,   // cut, plunge, link, rapid
    error:   ErrorBound<Length>,
}
pub record PassKey     { level: u32, region: EntityId, index: i32 }   // depth level, region anchor, index from the region's origin
pub record WorkOffset  { number: WcsId, frame: CoordSys }             // G54 to G59, extended and fixture offsets
pub record Station     { part: Instance, stock: Body, wcs: WorkOffset }
pub record Setup       { machine: Machine, fixture: Assembly, stations: [Station], index: Option<RotaryIndex> }
pub record Workingstep { target: Query, strategy: StrategyCall, station: StationRef, toolpath: Toolpath,
                         comp: CompMode, wear_range: Range<Length> }   // Computer | Control | Wear | ReverseWear
pub record Program     { setups: [Setup], steps: [Workingstep], order: Order }   // ByTool | ByStation
```

Four rules follow from this model.

**Decision D-MFG-1:** Every manufacturing capability follows the contract's layers: intent in Ingot, heavy search in Wasm components, geometry in Anvil and physics in Flux.
*Why:* shops edit intent, search algorithms need sandboxed native speed, and shared operations serve CAM, slicing, moulding and inspection alike.
*Rejected:* a monolithic CAM engine, which would be privileged code; strategies written entirely in Ingot, whose inner loops are too hot.

**Decision D-MFG-2:** Manufacturing adds no geometry or result types: things are Bodies, Parts and Assemblies, paths are wire Bodies carrying Fields, and results are Fields.
*Why:* the UI already paints, diffs, caches and queries these types, so a toolpath or a warpage result needs no new viewer.
*Rejected:* separate stock, toolpath or result types, which would be parallel abstractions.

**Decision D-MFG-30:** A parameter of the material alone is a COV `Material` property, such as Cross–WLF rheology, Tait pvT, solidus, liquidus or cure kinetics. A property of the material in a stated condition stays COV's even when the condition names a process or machine, and a parameter of material and equipment together, such as melt-to-mould heat transfer, is MFG process data citing COV's model id.
*Why:* no parameter may have two owners, and the split follows what the parameter physically depends on.
*Rejected:* everything in COV, because machine data are not material data; a split per process, because melts and alloys straddle processes.

**Decision D-MFG-22:** A toolpath is a wire Body with one edge per run of one motion kind, each a polyline or arc-spline with Field samples. Its edges are grouped into passes keyed by `PassKey`: the depth level, the anchor `EntityId` of the region being cut, and the pass index counted from the region's declared origin. Edits and diagnostics address passes by key; a single move is addressed by (pass key, vertex index) only for display.
*Why:* a finishing path has millions of moves, so an edge per move would carry identity and history each, while a pass key is keyed by provenance like a pattern generator's keys and therefore survives regeneration.
*Rejected:* one edge per move, which multiplies memory and hashing by orders of magnitude; addressing by (edge `EntityId`, vertex index), which regeneration renumbers; a toolpath type outside `Body`.

Finishing workingsteps declare `comp`, the cutter compensation mode, which is `Computer` by default. In the other modes the post emits G41 or G42 with the D register, and the gouge and collision checks run at both ends of `wear_range`. Wear adjustments that a machinist enters at the control therefore stay inside what was verified.

**Decision D-MFG-3:** Randomized searches take an explicit `seed` and a counter-based generator, and parallelism runs as a seeded portfolio. Budgets count work units, shown as an estimated time on the reference laptop, and "continue" warm-starts with a larger budget.
*Why:* the contract forbids clocks in evaluation, yet users who expect "run for 10 minutes" still get an estimate they can reason about.
*Rejected:* wall-clock limits, which are not reproducible; shared-state parallel search, which depends on thread order.

Kiln keeps the best portfolio result by (objective, seed), and outputs quantize before locale-free formatting, so two machines produce byte-identical NC text. Outside data enter only as External inputs (prices, offers, machine readings) or Evidence records (part measurements), each pinned in `ingot.lock` and named by `ObjectId` in the outcome of every check that read it.

Every failure is a typed `MfgError` whose fixes are typed edits, listed in the Reference section. No strategy substitutes a tool, direction or material silently. A search that reaches its budget returns the cacheable `Failure` `kiln/work_limit` with its best result so far beside it (contract 7.2), since a search budget is an argument; an Evaluation's own `Budget` running out is the Abort `BudgetExhausted` (contract 7.2), which is never cached.

Process profiles declare the representations their hand-off accepts and the `realize:` point their exports use, `Mid` for machining by default, recorded in the export record. A 3MF process accepts implicit and mesh regions; a STEP process accepts only B-rep, which shops' CAM and coordinate measuring machine (CMM) software read. A part with an implicit fallback region from MEC therefore releases for a STEP process only after conversion within tolerance, and no semantic PMI (product and manufacturing information: tolerances and notes the machine can read) may target such a region.

What MFG owns, and what it leaves to others:

| Area | MFG owns | Others own |
| --- | --- | --- |
| Process planning | Setups, workingsteps, toolpaths, posts, nests, builds, routings, setup sheets | None |
| Process physics | Process setups, boundary conditions, process data, checks | FLX (forms, solvers); COV (models, envelopes) |
| Design checks | Process checks for manufacturability, assembly and additive design against process profiles | MEC (design checks); ELX (board rule checks) |
| Product structure | Routings, program Items, as-built records | KLN (Items, BOM views, change orders) |
| Electronics and harnesses | The factory hand-off: packages, rule packs, panels, stencils, test, harness package | ELX (board, rule checks, connectivity); MEC (harness geometry); ECO (`io/` writers) |
| Connectivity | Machine, printer and CMM protocol mappings; `apps/machine-gateway` | PLT (packaging, serial ports, certificates); AGT (`api`, Acts) |

MFG writes Rust in exactly three places, as contract 12 allows: operation families inside `flux-op-*` crates, Wasm components under `std/mfg/`, and the `apps/machine-gateway` service. The Reference section lists each; everything else is Ingot.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Core manufacturing types | `std::mfg::core` records over Bodies, Fields and Assemblies | Typed compile errors | MFG-O-CORE-1 | 0 |
| Typed failures with fixes | Every `MfgError` carries ranked typed edits | The `MfgError` itself, with fixes | MFG-O-CORE-1 | 0 |
| Seeded, budgeted searches | `seed` and work-unit `budget` arguments; seeded portfolios; warm-started "continue" | `kiln/work_limit` with the best result | MFG-O-DET-1 | 0 |
| Outside data | External inputs and Evidence records, pinned in `ingot.lock` and named by `ObjectId` in the `CheckOutcome` | `MissingData` naming the input | MFG-O-CORE-2 | 1 |
| Representation acceptance | Accepted representations per process profile; the fallback-region rule | Release blocked, naming region and process | MFG-O-CORE-4 | 1 |
| Label invariance | Plans and costs unchanged when every name is re-randomized | None: names never enter a plan's inputs | MFG-O-LABEL-1 | 1 |
| Toolpath storage and pass keys | Wire Bodies with keyed passes; target 10⁷ moves under 400 MB | `Infeasible` above the declared move count | MFG-O-CORE-3 | 2 |

## Machines, controllers and posts

A program is only as safe as the model of the machine it was simulated on, so this section defines machines, their controllers and the post engine that writes their programs.

A machine is an Assembly of links joined by MEC's kinematic mates, plus axis limits, spindles, a tool changer and a controller record. Volumetric compensation stays on the control; Crucible models the nominal machine and the control's declared behaviour.

```
pub record Machine {
    structure: Assembly, chain: KinematicChain,
    axes:      [Axis],                   // linear and rotary (A, B, C) with travel, rapid, acceleration and jerk
    spindles:  [Spindle],                // Field<AngularVelocity, Power>, Field<AngularVelocity, Torque>
    tool_changer: Option<ToolChanger>, channels: [Channel], controller: Controller, envelope: Body,
    qualified_versions: VersionRange,    // controller software versions MFG's capture has qualified
}
pub record Controller {
    family: ControllerFamily, dialect: Dialect, flags: CapabilityFlags,
    offsets: OffsetModel,                // work offsets, H and D registers
    motion:  MotionSemantics,            // how the control really moves
    macros:  MacroLibrary,               // control-resident macros, under their licences
    files:   FileRules,                  // writing rules and storage normalizations
}
```

### Building a machine package

A shop evaluating CAM first asks whether its machines are already there. Machine builders rarely publish open kinematic models, so Crucible builds packages from what builders do publish: a STEP model of the machine and its specification sheet.

```
let vf2 = machine(
    structure: asset("haas_vf2.step"),
    axes: [Axis { joint: q.slide("X"), travel: 762mm, rapid: 25.4m/min, accel: 5m/s2, jerk: 50m/s3 }, …],
    spindles: [shop::spindles::vf2_8100],
    tool_changer: shop::changers::umbrella_20,
    controller: std::mfg::controllers::haas_ngc,
)
```

`machine` checks four things and fails with a typed `MachineModel` error naming the one that fails:

- the kinematic chain closes;
- the axis travels match the specification sheet;
- the home pose is collision-free;
- the pivot and offset lengths agree with the kinematic parameters stored in the control, read through a gateway connector.

The last check is what makes a package trustworthy: the control's own parameters are the machine builder's calibration of that serial.

Phase 2 ships parameterized templates for the common configurations: the 3-axis vertical machining centre, table-table and head-table 5-axis machines, the two-axis lathe and the mill-turn centre with a sub-spindle. A shop fills in limits, envelopes and the controller record. The reference shop's machines ship as complete packages. A template-built machine is offered for transfer only after its post qualification passes, described below. ECO lists the machine-definition formats Crucible reads, each with its licence check.

**Decision D-MFG-36:** Machine packages are built from the builder's STEP model and specification sheet or from a parameterized template, and each is checked against the kinematic parameters stored in the control before any program for it can pass simulation.
*Why:* builders publish geometry and specifications but rarely kinematic models, and the control's stored parameters are the only independent record of the real machine.
*Rejected:* waiting for builders to publish machine packages, which leaves shops without machines in phase 2; importing kinematic models from other CAM systems' libraries, whose formats and licences vary per vendor.

### Controllers and how they really move

Programs crash in motion the control interpolates rather than motion the CAM system drew: dog-leg rapids, rotary unwinding, reference returns, canned-cycle retracts, cutter-compensation entry and tool changes. `MotionSemantics` records each of these per controller.

```
pub record MotionSemantics {
    source: SemanticsSource,             // Declared { corpus } | VendorKernel { host_image }
    rapid: Rapid,                        // Linear | PerAxis { rates }
    rotary_rapid: RotaryRapid,           // Shortest | Directional | Unwind
    tcp_in_rapid: Bool, reference_return: ReferenceReturn, cycle_retract: Retract,
    cutter_comp: CutterComp,             // look-ahead blocks, entry rule
    tool_change_envelope: Body,
}
```

**Decision D-MFG-23:** Collision simulation and the independent re-interpreter both execute the posted NC text under the controller's `MotionSemantics`, never the pre-post toolpath. An undeclared semantic sweeps a conservative envelope and returns `Unsupported` instead of passing.
*Why:* programs crash in the motion the control interpolates, and controls do not promise straight rapids [Haas G-codes].
*Rejected:* checking the toolpath only; assuming straight-line rapids.

Posts convert G0 to G1 at a declared rapid-equivalent feed wherever the rapid envelope comes closer to stock or fixture than the clearance.

A declared semantics comes from a capture. The reference shop runs a corpus of probing programs on each controller family in a program-test mode that interpolates with the axes still, such as Haas's graphics mode [Haas operation], and the recorded traces must match the declaration within tolerance. A family's post ships only when that capture passes.

A shop whose control is not yet among the supported families need not wait. It runs the same published capture procedure in program-test mode on its own control, and the gateway signs the resulting traces with its device key. The `MotionSemantics` record and corpus enter the shop's own machine package through a Proposal that the shop's named qualifier merges under its branch rule, scoped to its tenant and serials. The qualification comparison runs on it unchanged, and the approval page labels programs for that machine class "shop-qualified". A family becomes generally supported when the reference shop's own capture confirms it.

The controller's software version is instance data, not part of the machine class. At transfer the gateway reads it and checks it against the package's `qualified_versions`; a version outside the range blocks transfer with `ControllerVersionUnqualified` until the capture runs once for that version. If the recaptured `MotionSemantics` digest is unchanged, the machine class and every Approval granted against it persist, so a routine control update does not void a shop's approved programs (contract 7.6).

For Sinumerik controls, NX CAM runs the controller maker's own virtual NC kernel, which Siemens describes as a model "provided by the controller manufacturer" whose simulation "responds exactly like a real machine" [NX VNCK]. From phase 3 a `MotionSemantics` may name such a kernel as its source.

**Decision D-MFG-37:** A controller maker's virtual kernel runs as an External Op under the customer's licence, and its motion trace drives the collision and gouge checks for that family at `SignOff`. Declared semantics remain the `Interactive` path and the fallback, and a differential oracle compares the two on the crash corpus.
*Why:* a declared model can only bound vendor cycles or report `Unsupported`, while the maker's kernel executes cycles, subprograms and look-ahead as the control does.
*Rejected:* declared semantics only, which leave high-end 5-axis users below what they already have; linking a vendor kernel into the engine, which the licence rules and determinism grades forbid.

The kernel runs on untrusted-evaluation workers in a pinned host image with egress denied except a granted licence-server endpoint, so its inputs are limited to `internal` labels without `controls` unless a two-person grant names the host (contract 7.8). A `SignOff` verdict accepts its trace when two single-use runs on different hosts agree; otherwise the result is `Unverified` and decides nothing without a policy allowance. Sinumerik comes first because Siemens documents its kernel.

### The post engine

**Decision D-MFG-5:** Programs are stored in one form mirroring ISO 14649, each workingstep binding a target, a strategy with tool and technology, and a toolpath. One post engine, a Wasm component, maps it to a dialect through the `Controller` record, data and Ingot hooks.
*Why:* STEP-NC export becomes a mapping, every block traces to its workingstep, and shop post editors work in Ingot rather than a vendor scripting language.
*Rejected:* posting from cutter-location files, which loses intent; a post per strategy and machine; Rust hooks by default.

Hooks run on `on_program_start`, `on_tool_change`, `on_wcs_change`, `on_rapid`, `on_cycle` and `on_program_end`. G-code comes only from this engine, through the `crucible:mfg` `post-processor` world.

**Decision D-MFG-31:** Posts emit a restart point at every workingstep and tool change: a sequence number, then a full restatement of modal state and a clearance-plane approach. Simulation verifies each entry, the setup sheet lists them, and a restart inside a workingstep is `Unsupported`.
*Why:* operators restart by block search after a broken tool or a power loss, and a restart that skips a tool call or an offset crashes.
*Rejected:* full runs only, because operators restart anyway; restarts anywhere, because the modal state there is unchecked.

ISO 6983-1:2009 defines the program format and address words, and it was confirmed in 2025 [ISO 6983-1]. Posts read capability flags, not vendor names; the Reference section maps each flag to the codes of four families from vendor documentation. Where Fanuc names a function without its code, the conformance corpus fixes it, and Mazak controls are programmed in ISO mode, never Mazatrol.

Qualification closes the loop between a post and a shop. The shop supplies a program it has already proven on a reference part; Crucible's post for the same plan must equal it up to a declared list of differences, and the captured corpus must match `MotionSemantics`. The record lists the serials qualified for the class. A post release that reproduces a program's canonical hash keeps that program's Approval; one that changes it needs a new Approval, and the approval page shows the semantic NC diff.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Machine package builder | `machine(structure: Asset, axes: [Axis { joint: Query, travel, rapid, accel, jerk }], spindles, tool_changer, controller) -> Machine` from the builder's STEP and specification sheet | `MachineModel { check }`: open chain, travel mismatch, home-pose collision, or disagreement with the control's stored kinematic parameters | MFG-O-KIN-3 | 2 |
| Machine templates | 3-axis vertical machining centre, table-table and head-table 5-axis, two-axis lathe, mill-turn with sub-spindle; the reference shop's machines as complete packages | Transfer refused until post qualification passes | MFG-O-KIN-3 | 2 |
| Forward and inverse kinematics | `fk` per channel; closed-form `ik` for table-table, head-head and head-table, damped least squares otherwise; every branch | `AxisLimit`; `Unreachable` with the nearest pose | MFG-O-KIN-1 | 2 |
| Rotary indexing and wrapping | 3+1 indexing on A or B; 2D paths wrapped onto cylinders | `AxisLimit` | MFG-O-KIN-1 | 2 |
| Singularities and rotary linearization | Branches minimize rotary travel; points inserted until tip deviation is in tolerance | `Infeasible` with the segment | MFG-O-KIN-2 | 3 |
| Kinematic and spindle limits | Feed limited by per-axis velocity, acceleration and jerk; power and torque against spindle Fields | `Infeasible` with segment and margin | MFG-O-KIN-2 | 2 |
| Motion semantics | Declared per controller from a captured corpus; the G0-to-G1 rule | `Unsupported` if undeclared | MFG-O-SIM-2 | 2 |
| Shop-qualified families | The published capture procedure run on a shop's own control; gateway-signed corpus merged by the shop's qualifier; scoped to tenant and serials; labelled on the approval page | Qualification failure lists the differing traces | MFG-O-POST-3 | 2 |
| Controller versions | Software version as instance data checked at transfer against `qualified_versions`; recapture keeps the class when the semantics digest is unchanged | `ControllerVersionUnqualified` | MFG-O-POST-3 | 2 |
| Vendor controller kernels | `VendorKernel { host_image }` as a `MotionSemantics` source, run as an External Op under the customer's licence; Sinumerik first | `Unverified` without two-host agreement; `Unsupported` without a licensed image. Requires: KLN External Op receipts | MFG-O-SIM-7 | 3 |
| Generic ISO 6983 post | `post(program, machine) -> (NcText, BlockMap)` with arcs, helices, compensation and cycles | `Unsupported { capability, controller }` | MFG-O-POST-1 | 2 |
| Fanuc, Haas, Siemens and Heidenhain posts | 3-axis, 3+1 and 3+2 | `Unsupported { capability, controller }` | MFG-O-POST-1 | 2 |
| Simultaneous 5-axis posts | Four families; tool centre point control, or joint space with inverse-time feed | `AxisLimit` or `Unsupported` | MFG-O-POST-1 | 3 |
| Okuma OSP and Mazak ISO-mode posts | Family offset and cycle conventions | `Unsupported { capability, controller }` | MFG-O-POST-1 | 3 |
| Mitsubishi, Brother and Hurco posts | Family offset and cycle conventions | `Unsupported { capability, controller }` | MFG-O-POST-1 | 4 |
| Post configuration and hooks | Customizations as Ingot data; Ingot hooks; Rust hooks only under contract 4 | Errors name the hook | MFG-O-POST-2 | 2 |
| Restart points | A restart point at every workingstep and tool change | `Unsupported` inside a workingstep | MFG-O-SIM-6 | 2 |
| Macro libraries | Control-resident macros from the control or their maker, in the machine package | `Unsupported { macro }` unless a declared envelope bounds the call | MFG-O-SIM-3 | 2 |
| Post qualification | The shop's proven program against Crucible's on a reference part; corpus captured on physical controls; a record of the serials qualified for the class | Undeclared differences block it | MFG-O-POST-3 | 2 |
| Semantic NC diff and block map | Motion and technology diff ignoring formatting; each block mapped to workingstep, path parameter and feature | None: both are total functions of two parsed programs | MFG-O-POST-4 | 2 |

## Tools, stock, setups and workholding

A program is checked against the tools, stock and fixtures that will really be on the machine, so this section defines them and the drawings a machinist works from.

A tool is an Assembly of catalog parts with ISO 13399 properties as typed quantities [ISO 13399-1]. Vendors publish ISO 13399 data [Sandvik Coromant tool data], and ToolsUnited serves ISO 13399 and DIN 4000 data [Mitsubishi Materials]. Presetter readings and offset tables enter as External inputs per tool assembly serial.

**Decision D-MFG-6:** In-process stock serves leftover display, rest machining and the hand-off between setups, while gouges are the certified distance between each move's swept envelope and the design B-rep. Stock is an `Implicit` Body on a sparse narrow-band grid unless a benchmark before phase 2 shows tri-dexel meeting GP3's tolerances in less memory.
*Why:* stock for a GP1-sized part at 5 µm needs about 8 × 10⁹ band cells against a 1 GiB memory target, so the grid cannot also be the gouge reference.
*Rejected:* gouge checks on the grid, which are resolution-limited; exact B-rep stock, whose cost grows per move; meshes only, which leave slivers.

A setup holds stations, so double vises, tombstones and pallets are ordinary data. `setup_sheet` builds the machinist's drawing in Ingot: program number, work offsets dimensioned to datums, fixtures, stock and the steps a person at the machine must take. Its tables list tools with gauge lengths and verified offsets, and workingsteps with times, compensation, wear range and restart points.

Multi-operation parts also need in-process drawings: the shape after setup N, with the allowance left for grinding or heat treatment, which machinists and inspectors work to between operations. `in_process_drawing(program, after: op1, template)` builds one from setup N's output Body, dimensions it from that setup's datums, lists the allowance per face, and carries the characteristics MFG's balloon allocator labels as in-process, so an in-process check is measured and traced like a final one.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tool catalog import | ISO 13399 Part 21 data, DIN 4000 mapping and documented tool-library formats to catalog parts | `MissingData` per absent property | MFG-O-TOOL-1 | 2 |
| Tool assembly | `assemble_tool(cutter, holder, extensions, stickout) -> Instance`; full collision Bodies | `Infeasible` on interface mismatch | MFG-O-TOOL-1 | 2 |
| Presetter readings | Length, radius and runout as External inputs per assembly serial | Missing or stale readings flagged | MFG-O-TOOL-1 | 2 |
| Per-machine tool tables | Nominal tools by T number for posts; pockets and H and D values checked at transfer | Conflicting entries fail | MFG-O-TOOL-1 | 2 |
| Cutting data | Vendor data, shop values, mechanistic coefficients and life parameters with source and uncertainty | `MissingData` only without any source | MFG-O-FEED-1 | 2 |
| Tool life | Count-based per edge from as-run records (2); model-based from engagement (4) | Tools past life flagged | MFG-O-TOOL-2 | 2, 4 |
| Blank and hand-off | `stock(kind, material, size or Body, cert)`; setup N's output stock is setup N+1's blank | Part outside stock; fixture hits stock | MFG-O-STOCK-1 | 2 |
| In-process and rest stock | `simulate(program) -> (Body, Field<Body, u32>)`; `rest(stock, part, tolerance) -> Body` | `OutsideEnvelope` when the grid misses the tolerance | MFG-O-STOCK-1 | 2 |
| Setups and stations | `Setup { machine, fixture, stations }`; tombstones and pallets | Duplicate work-offset registers fail | MFG-O-SETUP-1 | 2 |
| Setup sheet | `setup_sheet(program, template) -> Drawing` | Tools without gauge data listed | MFG-O-SETUP-1 | 2 |
| In-process drawings | `in_process_drawing(program, after: SetupRef, template) -> Drawing` from the hand-off Body; datums of that setup; allowance per face; in-process characteristics | Unresolved datums or characteristics listed | MFG-O-SETUP-1 | 2 |
| Vises and modular fixtures | Catalog parts with jaw stroke and clamping force | `Collision` with toolpaths | MFG-O-SIM-2 | 2 |
| Soft jaws and offset probing | Jaw Bodies offset from the part with their own program; probing cycles that set work offsets | `Unreachable` points | MFG-O-SETUP-2 | 2 |
| Locating, clamping and jigs | Form closure by contact-wrench rank; clamp forces with friction and Flux deflection (3); weld and assembly jigs | `Infeasible` naming free motions; slip or deflection | MFG-O-SETUP-3 | 2, 3 |

## Milling, drilling and probing strategies

Strategies are where a CAM system earns its keep, so this section fixes how each one is built, what bound it guarantees and how it is measured.

Each strategy is a `toolpath-strategy` Wasm component that turns a setup, a target region, a tool, parameters, a tolerance, a seed and a budget into a `Toolpath` with keyed passes. Contact between the cutter and the surface is Anvil's `tool_contact`, a clean re-implementation of the drop-cutter and push-cutter algorithms. OpenCAMLib implements them under LGPL-2.1 [OpenCAMLib] with little recent activity [Open Hub OpenCAMLib], so it serves only as a reference oracle. Two-dimensional offsets for pockets, profiles and kerf use cavalier_contours, which keeps arcs exact [cavalier_contours].

### Roughing that holds its engagement

High-efficiency roughing is the strategy machinists rely on most. Its purpose is to keep the tool's engagement angle (how much of its circumference is in the material at once) and its chip thickness steady. The tool can then run deep at high feed without the load spikes that break it in corners. Every incumbent ships a version: Mastercam's Dynamic Motion [Mastercam], Fusion's 3D Adaptive Clearing [Fusion adaptive], hyperMILL [hyperMILL] and NX CAM [NX CAM].

Crucible ships two roughing strategies measured by the same engagement oracle. The first ships in phase 2 whatever any patent opinion says.

**Decision D-MFG-35:** Engagement-limited offset clearing is the roughing strategy that ships in phase 2 unconditionally: offset passes whose engagement against the true in-process stock is checked at every step, with trochoidal loops inserted wherever the bound would fail.
*Why:* the strategy shops need most cannot wait on counsel, and offset clearing with measured engagement uses only long-established techniques while meeting the same measurable bound.
*Rejected:* offset pockets without the engagement check, whose engagement spikes at corners; shipping no high-efficiency roughing until the patent opinion arrives.

The second, adaptive clearing, grows the cleared region in a spiral at constant engagement. Claim 1 of Boeing's US 9,164,503 covers one such method [US 9,164,503]. It computes a medial-axis transformation, cuts a pre-roughing slot along a medial-axis curve with a circular recess at each end, and then spirals outward from inside that slot at a constant radial depth of cut. Google Patents shows its anticipated expiry as 22 February 2034, and its citing documents include toolpath patents of Plethora, D.P. Technology and Siemens.

**Decision D-MFG-7:** Adaptive clearing is a clean-room design-around measured against the true in-process stock. It never cuts a pre-roughing slot; it enters by one helix or ramp at the point of maximal clearance or at a pre-drilled hole and grows the cleared region from there. Its bound is the maximum engagement angle and chip thickness, which the oracle measures independently, and it ships only after counsel's freedom-to-operate opinion, a phase 1 gate item (contract 13.1).
*Why:* vendors document behaviour but not their algorithms, so the measurable bound is the contract, and the method omits the claim's slot element by construction.
*Rejected:* any method with a pre-roughing slot along a medial-axis curve; copying one vendor's documented method.

The adaptive steps, listed for counsel with the claim elements each omits:

1. Compute the medial axis of the region minus the tool radius with exact predicates, used only to rank entry points and necks; no toolpath follows it.
2. Enter by helix or ramp at the vertex of maximal clearance, or at a pre-drilled hole. There is no slot and no pair of end recesses.
3. Grow the cleared region in steps, each solved so that engagement against the current stock equals the requested angle; the radial step varies, so the depth of cut is not constant.
4. Where the bound cannot hold (necks, corners), switch to variable-radius trochoids.
5. Link passes with tangent-continuous, collision-checked moves inside cleared material, and set feed from chip thinning.

Trochoidal slotting, the circular-loop strategy for full-width slots, is its own row with its own opinion, so a finding against one does not hold back the other.

### The other milling strategies

Finishing strategies trade scallop height against time: parallel and scallop passes for gentle surfaces, waterlines for steep walls, pencil passes in corners, and flowline passes along a face's parameter lines. Drilling cycles come from MEC's `HoleSpec`, so the hole's size, depth, thread and fit drive spot, drill, peck, ream, bore and tap without being retyped. Probing paths come from the inspection plan, and any cycle that writes a work offset is flagged on the setup sheet.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Face, pocket, contour and rest (2.5D) | Offset or zigzag depth steps, island-aware, ramp or helix entry; rest passes where material remains | `Unreachable` where narrower than the tool | MFG-O-MILL-1 | 2 |
| Engagement-limited offset clearing | Offset passes with engagement checked against true stock; trochoidal loops where the bound fails | `Infeasible` with the achieved maximum | MFG-O-MILL-2 | 2 |
| Adaptive clearing | The design-around spiral from a single helix or ramp entry, constant engagement against true stock | `Infeasible` with the achieved maximum | MFG-O-MILL-2 | 2, after counsel's opinion |
| Trochoidal slotting | Trochoids varied per period [Li et al. 2025] | `Infeasible` with the achieved maximum | MFG-O-MILL-2 | 2, after its own opinion |
| Parallel, scallop and waterline finishing | `tool_contact` to chord tolerance; constant scallop; steep-and-shallow split | `Unreachable` areas listed | MFG-O-MILL-3 | 2 |
| Pencil, flowline and isoparametric | Bi-tangent corner passes; iso-curves re-spaced to a scallop bound | Degenerate parameterization reported per face | MFG-O-MILL-3 | 2 |
| Deburr, chamfer, engraving and thread milling | Edge-chain passes at size; V-carve from the medial axis; analytic helices | `Unreachable` edges; `Infeasible` tool fit | MFG-O-MILL-4 | 2 |
| Drilling cycles | Spot, drill, peck, ream, bore, tap and back-bore from MEC's `HoleSpec`; shortest tour | `Unsupported` cycle, expanded into moves | MFG-O-MILL-4 | 2 |
| Probing paths | Touch points from the inspection plan; offset writes flagged | `Unreachable` points | MFG-O-SETUP-2 | 2 |
| 5-axis swarf, multi-axis and barrel finishing | Flank passes on ruled walls; collision-aware tilt from any 3-axis pattern; barrel profiles | `Infeasible`, `Collision` or `AxisLimit` | MFG-O-MILL-5 | 3 |
| 5-axis roughing | Engagement-limited clearing in tilted frames chosen by access analysis | `Infeasible` with the achieved maximum | MFG-O-MILL-2 | 3 |

## Toolpath editing

Programmers fix small problems by editing the toolpath, not by re-tuning a strategy, so this section gives them those edits without losing associativity.

A machinist finds an air cut, a clamp the plan did not know about, or a pass better split between two tools. Fusion lets the programmer "trim parts of a milling toolpath that are contained by a polygon, plane, or boundary" [Fusion trim] and delete "a selection of passes or segments" [Fusion delete passes]. In Crucible the same edits are ordinary Ingot features in `std::mfg::modify`, written after the strategy call:

```
use std::mfg::modify::{trim, remove_passes, relink, feed_scale}

let rough  = offset_clearing(op1, op1.removal(), tool: em_10_3fl, max_engagement: 70deg, allowance: 0.3mm)
let clear  = rough |> trim(by: Boundary(op1.fixture.face(role: jaw_top)), keep: Outside)
let lean   = clear |> remove_passes(keys: [PassKey { level: 0, region: op1.removal().anchor, index: 7 }])
let linked = lean  |> relink(rules: shop::links::stay_down)
let gentle = linked |> feed_scale(region: p.face(role: end_cap).near(3mm), factor: 0.7)
```

| Edit | What it does |
| --- | --- |
| `trim(tp, by: Polygon \| Plane \| Boundary(Query), keep: Inside \| Outside \| Both)` | Cuts passes at a boundary; `Both` splits the toolpath in two |
| `remove_passes(tp, keys)` | Deletes passes by key |
| `reverse(tp, keys)` | Reverses the cutting direction of passes |
| `reorder(tp, by)` | Reorders passes by a key list or a rule (shortest link, by region, climb first) |
| `relink(tp, rules)` | Recomputes links and leads between passes under stay-down, retract or clearance-plane rules |
| `entry(tp, at: Query)` | Moves the entry point to a chosen location |
| `feed_scale(tp, region, factor)` | Scales feed inside a region |
| `change_tool(tp, tool)` | Swaps the tool where its cutting profile matches the original's, keeping the passes |

**Decision D-MFG-38:** Toolpath edits are features that resolve passes by `PassKey` and re-run the gouge, collision and engagement checks on every new lead and link. A key that disappears after regeneration is a `ResolveError` with fixes, never a silent re-target.
*Why:* an edit written into the program survives the next design change and is reviewed like any other line, while the pass key makes "the same pass" a matter of provenance rather than position.
*Rejected:* editing the posted NC text, which turns the program into a legacy program without associativity; edits stored as move indices, which regeneration renumbers; edit state kept inside a CAM session, which nobody can review or diff.

`change_tool` fails with `Infeasible` when the new tool's cutting profile (diameter, corner radius, flute length below the holder) differs from the original's, and its fix is to regenerate the workingstep with the new tool. UIX's toolpath playback selects passes and draws boundaries for these calls, so a person points at the pass and the edit is written as source.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Toolpath editing | `std::mfg::modify`: `trim`, `remove_passes`, `reverse`, `reorder`, `relink`, `entry`, `feed_scale`, `change_tool`, each resolving passes by `PassKey` | `ResolveError` naming a lost pass key, with fixes; `Infeasible` for a mismatched tool profile | MFG-O-PROG-6 | 2 |
| Re-checked edits | Gouge, collision and engagement checks on every lead and link an edit adds | `Gouge`, `Collision` or `Infeasible` naming the edit | MFG-O-PROG-6 | 2 |

## Turning, EDM, gears and grinding

Parts that rotate, parts cut by spark and parts that mesh need their own processes, and this section covers them along with the inspection that gears demand.

GP3's gears are cut by the shop from MEC's gear data table and MFG's inspection plan, while Crucible programs the housings, shafts and blanks. MEC owns gear geometry and the ISO 1328-1:2013 accuracy grade [ISO 1328-1], and COV owns gear, bearing and shaft ratings (contract 13.4). Phase 2 writes gear inspection plans as QIF 3.0 Plans with the gear data table as a PDF, through ECO's QIF writer, so a gear-measuring machine or CMM reads them directly. EDM tables come from machine packages; MFG does not model spark physics.

Turning starts from a revolved Body: the profile in the XZ plane drives roughing, finishing, grooving, parting and threading with insert clearance checked against the part. Mill-turn adds C and Y axes, B-axis tilting and the transfer to a sub-spindle, with workingsteps scheduled across channels so two tools never meet.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Turning | Revolved Body to XZ profile; rough, finish, groove, part and thread passes with insert clearance | `Infeasible` for non-revolved faces; `Unreachable` undercuts | MFG-O-TURN-1 | 2 |
| Adaptive turning | Constant chip-thickness roughing for heat-resistant alloys [Janus NX 2606] | `Infeasible` for non-revolved faces; `Unreachable` undercuts | MFG-O-TURN-1 | 3 |
| Mill-turn | C and Y milling, B tilting, sub-spindle transfer across channels | `Infeasible` with the conflicting window | MFG-O-TURN-2 | 3 |
| Swiss-type and channel balancing | Sliding headstock and gang tools; workingsteps assigned to channels | `Infeasible` with the conflicting window | MFG-O-TURN-2 | 4 |
| Wire EDM | 2-axis rough and skim with tabs; 4-axis taper with synchronized UV paths | `Infeasible` below wire radius plus overburn | MFG-O-EDM-1 | 3 |
| Sinker EDM electrodes | Electrode Body with spark gap, orbit and burn sequence | `Infeasible` when the electrode is not machinable | MFG-O-EDM-1 | 4 |
| Gear data and inspection | Profile, helix and pitch plans from the record's grade as QIF 3.0 Plans plus the PDF gear data table, for gear machines or CMMs. Requires: MEC Gear data tables | `MissingData` for an absent grade or data table | MFG-O-GEAR-2 | 2 |
| Gear generating | Hobbing and shaping as ISO cycle calls or a builder parameter set, named per family before it ships; power skiving after simultaneous 5-axis collision checking | `Unsupported`, with the fix 5-axis gear milling | MFG-O-GEAR-1 | 4 |
| 5-axis gear milling | Flank and root passes from the multi-axis strategies | `Infeasible`, `Collision` or `AxisLimit` | MFG-O-GEAR-1 | 3 |
| Grinding, broaching, honing and lapping | Gear and profile grinding with distortion allowance; surface and cylindrical grinding with a specific-energy burn check | `MissingData`; `OutsideEnvelope` | MFG-O-GEAR-1 | 4 |

## Sheet cutting, nesting and press brake

GP4's guards need profile cutting, nesting and press-brake planning in phase 2, each with an output a machine or its own software reads, and this section provides them.

MEC owns flat patterns, flat DXF export, the bend-allowance model (`BendRule`, `BendTable`) and self-clinching hardware rules; MFG owns how the sheet is cut and bent. Nesting places flat parts on sheets to waste as little as possible. Sparrow (MIT) runs guided local search [Gardeyn et al. 2025] on the jagua-rs collision engine, which is licensed MPL-2.0 [jagua-rs]. It matches or beats every best-known density on the ESICUP benchmark set, most clearly on SWIM (79.83% against 75.94%), under a 600 s default limit [sparrow].

**Decision D-MFG-9:** The 2D nesting Wasm component adopts the sparrow approach on a jagua-rs-style collision engine, with work-unit budgets instead of wall-clock limits.
*Why:* these are the leading open methods, both written in Rust and both buildable for Wasm; jagua-rs links under MPL-2.0 with its notice and source duties (contract 7.7).
*Rejected:* no-fit-polygon heuristics, which reach lower density; closed vendor libraries, which nobody can audit.

**Decision D-MFG-8:** Press-brake sequencing searches bend orders with collision checks between the partly bent part, the tools and the machine. Allowances come from MEC's sheet-metal model, springback from measurement, and from this tab's forming simulation once it lands in phase 5 (contract 13.4).
*Why:* one search handles every part, and the physics stays with its owners.
*Rejected:* rule tables per part family, which break on the first unusual part.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Profile cutting and ordering | Laser, plasma or waterjet paths with kerf, lead-ins, micro-joints, pierces, common lines and heat-aware order; a generic ISO 6983 cutting post with codes as `Controller` data, or DXF | `Infeasible` below kerf plus minimum web | MFG-O-CUT-1 | 2 |
| Flat-pattern hand-off | MEC's flat DXF export with layer convention and bend table per machine or shop. Requires: MEC Flat DXF export | Unmapped entities listed | MFG-O-CUT-2 | 2 |
| Press-brake planning | Bend sequence, tool stations and backgauge; allowance tables for MEC's `BendTable`; a bend sheet drawing with bent STEP and flat DXF (2); native bend programs for surveyed families (3) | `Infeasible` with the colliding bend | MFG-O-CUT-3 | 2, 3 |
| Waterjet taper, bevels and punching | Taper and corner compensation (3); 5-axis bevels (4); turret tooling, nibbling, repositioning (3) | `MissingData`; `AxisLimit`; missing tool | MFG-O-CUT-1 | 3, 4 |
| Sheet nesting | `nest(items, sheets, rules, seed, budget) -> Nest` with rotation, grain, spacing, zones and common lines | `Infeasible`; `kiln/work_limit` with the best nest | MFG-O-NEST-1 | 2 |
| Remnants, associativity and inventory | Remnant Parts; warm-started regeneration; mixed sheets by cost (3) | `Infeasible`; `kiln/work_limit` with the best nest | MFG-O-NEST-1 | 2, 3 |

## Feeds, speeds and chatter

Feed and spindle speed decide cycle time and tool life, and a wrong pair chatters or breaks the tool, so this section sets where the numbers come from and how far to trust them.

**Decision D-MFG-27:** Feeds and speeds default to vendor cutting data or the shop's proven values, labelled by source. The mechanistic model is an advisory check on power, torque, chip thickness and deflection until calibration upgrades the label.
*Why:* shops start from vendor tables, and a user without calibration cuts would otherwise get `MissingData` everywhere.
*Rejected:* mechanistic optimization by default, which needs calibration first; unlabelled values, which hide their basis.

With calibrated coefficients, `cutting_conditions(toolpath, material, machine, objective)` returns feed and spindle Fields that maximize removal rate. They are piecewise constant, quantized to the controller's increment, and labelled with each segment's binding constraint, so the programmer sees why a feed is what it is. The constrained optimization runs on Clarabel.rs, a permissive conic solver [Clarabel.rs].

Chatter is a self-excited vibration between tool and workpiece. Stability lobes map, for each spindle speed, the deepest cut that stays stable. MFG's receptance-coupling model gives the tool-tip frequency response from measured spindle responses and Flux's modal analysis, or a stored tap test takes its place. Zero-order lobes miss lobes that semi-discretization finds below about quarter-diameter immersion [Altintas et al. 2008].

**Decision D-MFG-10:** `Interactive` lobes use the zero-order solution and `SignOff` lobes semi-discretization, which low immersion, variable pitch and spindle-speed variation always use.
*Why:* this matches each method's published validity and keeps interactive updates under one second.
*Rejected:* zero-order everywhere, which misses low-immersion lobes; time-domain simulation by default, which is too slow and stays as an oracle.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Source-labelled defaults and calibration | Vendor or shop values by default; calibration cuts fit coefficients with uncertainty | `MissingData` only without any source; poor fits reported | MFG-O-FEED-1 | 2 |
| Advisory constraint check | Chip thinning, mechanistic force and power, spindle curve, roughness, cantilever or Flux deflection | `OutsideEnvelope` outside calibrated ranges | MFG-O-FEED-2 | 2 |
| Feed optimization and tool life | `cutting_conditions`; extended Taylor life per tool-material pair | `OutsideEnvelope`, never an extrapolated feed | MFG-O-FEED-3 | 3 |
| Tool-tip frequency response | `frf(tool, machine) -> Field<Frequency, Complex<Compliance>>` | `MissingData` without spindle receptance, with the fix "tap test" | MFG-O-CHAT-1 | 3 |
| Stability lobes and planning | `lobes(frf, coefficients, engagement) -> Field<AngularVelocity, Length>`; speed and depth in the stable region | `OutsideEnvelope` at low surface speed; no stable speed reported | MFG-O-CHAT-1 | 3 |
| Chatter feedback | Spindle-load or vibration data flag chatter and update the frequency response through a Proposal | `MissingData` when the machine reports no spindle-load or vibration signal | MFG-O-CHAT-1 | 4 |

## Machining simulation and NC verification

A program must be proven safe before metal is cut, so this section defines what simulation checks, on what text, and how programs from outside Crucible are verified too.

Simulation interprets the posted text under the controller's semantics, with conservative-advancement collision detection, so thin parts never slip between time samples. The crash corpus plants dog-leg rapids, unwinding, reference returns, wrong retracts, compensation gouges, tool changes and skipped restatements, and every family's simulation must find all of them.

**Decision D-MFG-28:** A product NC interpreter, separate from the oracle's, verifies NC from other CAM systems and hand programming, with macros from the machine package's library. Live system variables are typed inputs with ranges whose branches are explored up to a budget, and legacy programs declare the design revisions they were verified against in `verified_against`.
*Why:* shops hold thousands of proven programs that call macros and branch on probe results, and Crucible must check them without rewriting them.
*Rejected:* one shared interpreter, where a shared bug passes both; unknown macros treated as no-ops; converting legacy NC into workingsteps.

Legacy programs import as Assets and release as program Items on the same approval path, and programs that write offsets are flagged. Revising a `verified_against` revision returns a legacy program to `Prototype`, and `verify_nc` shows where the stock and the new design differ. UIX shows the NC text beside the toolpath through `BlockMap`, so a block and its move highlight together.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Material removal and leftover | `simulate(program)` streamed coarse to fine on narrow-band stock; signed stock-to-design distance Field | `OutsideEnvelope` when the grid misses the tolerance | MFG-O-STOCK-1 | 2 |
| Certified gouge check | Per move, certified distance between the swept envelope (`swept_volume`, `tool_contact`) and the design B-rep, at both ends of `wear_range` | `Gouge` with depth and block | MFG-O-SIM-1 | 2 |
| Machine collision and clearance | Continuous detection among links, tool, holder, fixture and stock on every posted move; near-miss Field | `Collision` with block and pair | MFG-O-SIM-2 | 2 (to 3+2), 3 (5-axis) |
| Controller motion | Rapids, unwinding, reference returns, retract planes, compensation entry, tool-change envelopes | `Unsupported` if undeclared | MFG-O-SIM-2 | 2 |
| External NC verification | `verify_nc(nc: Asset, machine, setup, tools) -> NcVerification` with the product interpreter | Parse errors; `Unsupported { macro }`; `Undecided` past the budget | MFG-O-SIM-3 | 2 |
| Restart verification | Each restart entry simulated from the tool-change position | `Collision` or `Gouge` naming the restart | MFG-O-SIM-6 | 2 |
| Cycle time | Jerk-limited kinematics with look-ahead, tool changes and dwell | `MissingData` when an axis lacks acceleration or jerk limits | MFG-O-SIM-4 | 2 |
| Vendor-kernel verification | Collision and gouge checks driven by a vendor kernel's motion trace at `SignOff`, compared with declared semantics | `Unverified` without two-host agreement; a differential mismatch fails the family | MFG-O-SIM-7 | 3 |
| Viewer cache | GPU tri-dexel render cache for playback, never a model | CPU rendering fallback, reported | MFG-O-SIM-5 | 2 |

## Programs, regeneration and agents

Programs must follow the design as it changes and be written by people or agents in the same way, so this section covers templates, recognition, regeneration and agent programming.

A workingstep finds its target through a `Query`, so Kiln recomputes only the workingsteps whose inputs changed, and a lost target is a `ResolveError` rather than a silent re-target. Shop templates are ordinary Ingot in the shop's package:

```
use std::mfg::{offset_clearing, finish_walls, StrategyCall, Pocket, Machine}

pub fn pocket_alu(p: Pocket, m: Machine) -> [StrategyCall] {
    let rougher  = shop::em_10mm_3fl
    let finisher = shop::em_6mm_4fl
    let rough = offset_clearing(p, tool: rougher, max_engagement: 12deg, stepdown: 1.5 * rougher.diameter)
    let walls = finish_walls(p, tool: finisher, allowance: 0mm, scallop: 2um)
    [rough, walls]
        .require(m.spindle.max_speed >= 12000rpm)
}
```

Native designs need no feature recognition, since Ingot features already know their holes and pockets. Imported B-reps go through rule-based matching and a learned panoptic segmenter whose targets a person or agent confirms. AAGNet reaches 97.44% panoptic quality on the MFInstSeg dataset, and FeatureFox exceeds 0.9 with about 250 training parts [FeatureFox].

**Decision D-MFG-34:** Learned recognizers train only on data licensed for commercial use of the weights, chiefly parts Crucible generates and labels from their features. Other datasets are benchmarks only; AAGNet's repository states no terms for MFInstSeg [AAGNet].
*Why:* the weights ship in a commercial product, and generated parts carry exact labels.
*Rejected:* datasets of unclear licence, whose weights could not ship; no learned recognizer, which leaves targets to be picked by hand.

Agents program as people do: Ingot on a branch, every oracle in CI, then a Proposal with cycle-time and tool-count deltas against the last approved program. CloudNC presents its CAM Assist output as a draft to review [CloudNC CAM Assist], and NX 2606 suggests strategies [Janus NX 2606]; Siemens has also announced work with Lambda Function on AI-assisted CNC programming [Siemens Lambda Function]. In Crucible an agent's program is no different from a person's: it cannot approve itself, prepare a transfer that skips simulation, or touch an oracle.

STEP-NC is ISO 14649, published in parts for process data, milling, turning, tools, EDM and additive manufacturing [ISO 14649 catalog]. AP238 edition 3 is ISO 10303-238:2022 [ISO 10303-238], and it adds geometry, GD&T (geometric dimensioning and tolerancing) and kinematics to the program [STEP Tools AP238e3]. G-code stays the shop-floor output; STEP-NC is an exchange format for programs between systems.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Incremental regeneration and diff | Only affected workingsteps recompute; geometric and technology diffs painted on geometry | `ResolveError` per lost target | MFG-O-PROG-1 | 2 |
| Templates, matching and setup planning | Ingot templates ranked by applicability predicates; targets grouped by access direction into setups | No match typed, never a silent default; `Unreachable` | MFG-O-PROG-2 | 2 |
| Target recognition | Rule-based (2) and learned (3) proposals on licensed training data; CPU inference with pinned weights | Unconfirmed targets never drive toolpaths | MFG-O-PROG-3 | 2, 3 |
| Agent-proposed programs | Branch, CI, Proposal, human Approval | Agents cannot approve, commit transfer Acts or edit oracles | MFG-O-PROG-4 | 2 |
| STEP-NC | ISO 14649 parts 10, 11, 12, 111 and 121 and AP238 through ECO's codec (3); parts 13, 14 and 17 (5) | `Unsupported` per workingstep; never invents feeds | MFG-O-PROG-5 | 3, 5 |

## Approval, transfer and physical safety

Simulation proves a program consistent with the model; this section binds the model to the shop floor as far as software can, and keeps the ceremony light enough that machinists use it.

Every program reaches a device by one path:

1. CI posts the program and runs every machining check on the posted text.
2. A named person approves the program subject on the approval page.
3. The program reaches a machine by an approved `send_to_machine` plan, or inside a bench session, or, once `Released`, by an operator's request at a qualified machine of its class.
4. The machine gateway checks the Approval, program number, hash and offsets before it writes anything to the control.
5. A person at the device selects the program and starts the cycle after the setup sheet's on-device steps.

The program subject is what the Approval signs, and contract 5.6 fixes its contents: `ProgramSubject { programs, machine_class, tools, setup_sheet, verdicts, block_map }`, meaning the canonical program digests, the machine class, the nominal tool assemblies by T number, the setup sheet, the simulation verdicts and the block map. A change to any of these voids the Approval. A rebase, a CI re-run or a pocket reassignment does not, because none of them changes the subject.

**Decision D-MFG-4:** An Approval binds to the `ObjectId` of the program subject, so a regenerated or edited program never inherits it. The subject names a machine class, {machine package digest, controller family, `MotionSemantics` digest, `FileRules` digest}, and nominal tools by T number, never a machine serial, a controller software version, a post version or a pocket.
*Why:* trust attaches to exactly what was reviewed, while sister machines, reassigned pockets and control updates are instance data that the gateway checks at transfer.
*Rejected:* approval per workingstep name, which would survive geometry edits; a serial-and-pocket subject, which needs an approval every shift; binding the controller software or post version, which voids every approved program at each control update or post release; signing the `ChangeId`, which a rebase changes.

### What the person approving sees and can do

MFG fills each physical-effect plan with the fields contract 7.6 requires of the approval page, from the device serial to the steps the person at the device must take.

Programs for a shop-qualified machine class carry that label.

The approver has the three outcomes of [AGT, Three outcomes](09-agents.md#three-outcomes). A shop lead who returns a program because of a feed in workingstep 3 gets a corrected plan back the same hour; only resubmitting the identical digest is refused.

### Prove-out and the minimum ceremony

A new program is proven at the machine: the machinist runs the first parts at reduced rapid and feed override, adjusts feeds, depths and clearances, and re-sends corrected versions. The state of the program Item decides what an edit at the control means.

**Decision D-MFG-39:** A program Item is created in `Prototype` by its first transfer plan, without a change order. An edit captured at the control of a `Prototype` program is prove-out: it opens a Proposal on the program Item's branch and enters the prove-out log, and the parts get no nonconformance. A nonconformance applies only when a `Proven` or `Released` program is edited at the control, and a manufacturing change order is needed only to enter `Released`.
*Why:* in prove-out, editing at the control is the work itself, and treating it as a quality event would flood the quality system and drive machinists to work outside Crucible.
*Rejected:* one rule for every state, which makes routine prove-out a stream of nonconformances; an order for every new program, which a one-off job never justifies.

The first-article record names the captured revision that actually ran, and `Proven` requires that revision merged into the program source, so the released program is the one that made the measured part. A one-off job that never repeats closes in `Prototype` with a run record linking program, part serials and results.

Repeated sends during prove-out use `bench_session`, one AAL3 Approval over the machine, the gateway and one program Item lineage ([AGT, Physical effects](09-agents.md#physical-effects)).

Whether the person who prepared a plan may also approve it is a policy, not a constant. The Cedar policy `self_approve_transfer` assigns the preparer as an eligible approver of their own transfer plans. It is off by default; enabling it is a widening Cedar change signed under contract 5.4, and the record names the site's safety officer. The approval still needs an approval credential at AAL3, and the audit log marks every self-approved transfer.

| Shop | How a program Item starts | Who approves a transfer | Prove-out | How work closes | When a change order is needed |
| --- | --- | --- | --- | --- | --- |
| One-person shop | Its first transfer plan, in `Prototype` | The machinist, under `self_approve_transfer` with AAL3 | Bench sessions; captured edits merge into the program source | A run record in `Prototype` for a one-off; `Proven` for repeat work | Only to enter `Released` |
| Job shop | Its first transfer plan, in `Prototype` | The shop lead or another assigned programmer | Bench sessions; returns for changes instead of denials | `Proven` after a first article; `Released` for repeat customers | Only to enter `Released` |
| Regulated production shop | Its first transfer plan, in `Prototype` | An assigned approver who is not the preparer; `self_approve_transfer` stays off | Bench sessions with a prove-out log reviewed at first article | `Released` through an order, with AS9102 or PPAP records | Every release and every change to a released program |

### The gateway

**Decision D-MFG-24:** The gateway sends only payloads whose full SHA-256 appears in a plan approved by credentials in its pinned approver directory, a signed, log-checkpointed list of credential public keys with their enrolment times. In its own core it also checks a canonical hash on read-back, overwrites only its own programs, checks instance data and captures edits, and it refuses a physical-effect Approval made with a credential enrolled less than 24 hours earlier.
*Why:* a header hash detects corruption but not substitution, controls rewrite formatting on storage, real offsets decide what runs, and a freshly enrolled credential may belong to whoever stole a session (contract 5.4).
*Rejected:* trusting the server's word that a plan was approved; hashing the posted bytes, which correct programs fail after the control reformats them; blocking edits at the control, which a gateway cannot do.

The canonical hash covers the token stream of the semantic NC parser, per dialect, without the header line. `FileRules` declares each control's storage normalizations, and a mismatch reports the semantic NC diff. The header comment carries the item, revision and 12 hexadecimal digits of the hash, so an operator can match the program at the control to the setup sheet.

Each program Item keeps one program number per machine class across revisions, and its subprograms travel with it. The gateway overwrites only an earlier revision of the same Item and otherwise fails with `ProgramSlotOccupied`. The setup sheet prints the number, and the approval page states what the transfer supersedes.

At transfer the gateway reads the offsets, checks D registers against `wear_range` and re-simulates with the actual gauge lengths. It then watches every referenced H, D and work-offset register until the program ends. A change that fails the check raises an alarm and an andon event within 5 s (target), but it cannot block the cycle, because only the control can.

Offsets and edits come from vendor connectors, DNC receive (the control sending its program back) or operator entry, and from phase 3 from MTConnect [MTConnect 2.5 Part 3]. An edited program opens a Proposal with its semantic NC diff; whether the parts need a nonconformance depends on the program's state, as above.

Drip feed streams a program too large for the control's memory, block by block. It is pull-only: `send_to_machine` stages the program in the gateway's DNC library and sends nothing. The gateway streams only on a request made at the control after the commit and after confirmation at its terminal. An already open session fails with `DncSessionPreArmed`, so a transfer can never complete a start the machine was already waiting for.

### Acts, payloads and wire-level rules

| Act or method | Effect | Rule |
| --- | --- | --- |
| `send_to_machine` | Stores a typed program or recipe in a device, or stages it for a pull | Never selects, loads or starts it |
| `send_robot_program` | Stores a robot program file in the controller's program store | Never through script, dashboard or real-time interfaces; never writes safety configuration |
| `store_machine_job` | OPC UA `Store` of a job order | The method allowlist below |
| `send_print_job` | Uploads a print job | Start parameters fixed false |
| `start_print` | Starts a material-extrusion print | Contract 7.6: a site safety record per serial and a confirmation at the printer |
| `bench_session` | Repeated transfers of one program or print lineage to one device for at most 8 hours | Each transfer keeps every gateway check; no start |
| `read.machine_data` | Status, offsets, program directory, alarms | A Read method (AGT), never an Act |

`send_to_machine` payloads are typed, one kind per kind of device: `NcProgram`, `DmisProgram`, `BendProgram`, `Recipe` (furnaces, ovens, reflow), `PlacementProgram` and `CutList` (harness machines). Each gets the plan check, the canonical hash, read-back where the device supports it and the program registry. Crucible starts none of these devices, and `unattended_safe` covers none (contract 7.6).

ISA-95 Job Control defines eleven job-order methods [ISA-95 Job Control]. Crucible calls `Store` only inside `store_machine_job`, and `Cancel`, `Clear` and `RevokeStart` only on unstarted jobs it stored itself; every other method is uncallable.

Upload calls can start a device. OctoPrint's upload takes `print` and `select` flags [OctoPrint files API], and Moonraker's takes `print` [Moonraker file manager]. PrusaLink honours a `Print-After-Upload` header [PrusaLink OpenAPI]. Universal Robots' interfaces accept URScript and load and play programs [UR client interfaces], so robot programs move only as files. Each connector manifest therefore lists its endpoints with fixed parameter values, which the gateway's core enforces outside the connector.

The EU Machinery Regulation applies from 20 January 2027 with cyber-safety provisions [EU Machinery].

[[DIAGRAM diagrams/07-manufacturing-program-release.jsx: program release flow · 14 steps from design to the person at the control]]

Read the flow from top to bottom: shaded steps are done by a person, red arrows return a typed error with fixes to the workingsteps, and the dashed arrow is edit capture back to a Proposal.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Program subject | `ProgramSubject { programs, machine_class, tools, setup_sheet, verdicts, block_map }`; Approvals sign its `ObjectId`; the machine class excludes controller and post versions | Any change inside voids the Approval, a changed setup sheet included | MFG-O-SAFE-1 | 2 |
| Program lifecycle and ceremony | `Prototype` from the first transfer plan; `Proven` from a first-article record naming the revision that ran; `Released` through a manufacturing change order; one-off jobs close with a run record | An EBOM-touching order is rejected; `Proven` refused while the run revision is unmerged. Requires: KLN Manufacturing change orders | MFG-O-SAFE-1 | 2 |
| Change impact | A design change returns exactly the programs whose targets, setups or `verified_against` revisions changed to `Prototype` | None: the affected set is computed and reported, never guessed | MFG-O-SAFE-1 | 2 |
| Transfer Acts and payload kinds | The Act table; typed `send_to_machine` payloads; bench sessions for prove-out | Refused without an approved subject or a live session. Requires: AGT Physical-effect Acts | MFG-O-SAFE-2 | 2 |
| Self-approval policy | `self_approve_transfer`, off by default, enabled by a widening Cedar change naming the safety officer; AAL3; audited | Refused while the policy is off; refused for agent-prepared plans the person did not delegate | MFG-O-SAFE-7 | 2 |
| Restricted print start | `start_print` per contract 7.6 | Refused for other processes, profile-only declarations or remote confirmations | MFG-O-SAFE-2 | 2 |
| Wire-level transfer verification | Manifest allowlists enforced in the gateway core (2); the OPC UA method allowlist (3) | Other requests dropped and reported | MFG-O-SAFE-3 | 2, 3 |
| Plan check and canonical hash | Full SHA-256 in a plan approved by the pinned directory; credentials younger than 24 hours refused; canonical hash on transfer and read-back | `PlanUnapproved`; `HashMismatch` with the diff | MFG-O-SAFE-2 | 2 |
| Program registry | One number per program Item and machine class; subprograms travel with it | `ProgramSlotOccupied` | MFG-O-SAFE-6 | 2 |
| Transfer-time offset verification | Offsets read, D registers inside `wear_range`, collision re-simulated with actual gauge lengths; controller version checked | `OffsetMismatch` beyond setup-sheet tolerance; `ControllerVersionUnqualified` | MFG-O-SAFE-4 | 2 |
| Offset watch | Checks re-run on each change to a referenced register; alarm within 5 s (target) | An alarm and andon event; it cannot block the cycle | MFG-O-SAFE-4 | 2 (vendor connectors), 3 (MTConnect) |
| Edit capture | Edit watch and DNC receive; a Proposal per edit; prove-out log in `Prototype`; nonconformance only for `Proven` or `Released` programs | Controls without edit signals need an operator declaration | MFG-O-SAFE-4 | 2 |
| Pull-only DNC and drip feed | Serial and Ethernet DNC with flow control, streamed only on a request at the control | `DncSessionPreArmed`; a fault stops the feed, resumed only at a restart point | MFG-O-SAFE-5 | 2 |

## Additive processes and build preparation

Additive manufacturing is phase 1's wedge, so this section defines the one pipeline every printing process shares and how a build reaches the printer or the bureau.

ISO/ASTM 52900:2021, confirmed in 2025, is the vocabulary standard [ISO/ASTM 52900]. Its seven process categories, first formulated by ASTM F42 [Loughborough AMRG], share one pipeline: build, orient, pack, support, simulate, compensate, slice and emit.

| Category | Layer output | Phase |
| --- | --- | --- |
| Material extrusion (filament, pellet, continuous fibre, concrete) | 3MF hand-off (1); G-code for Marlin, Klipper and RepRapFirmware, binary G-code (2) | 1, 2 |
| Powder bed fusion (laser, electron beam; metal, polymer) | 3MF for the bureau's build-preparation software (1); own scan vectors once a machine partner accepts an open vector format (4) | 1, 4 |
| Vat photopolymerization (SLA, DLP, masked SLA) | Layer images with exposure | 2 |
| Material and binder jetting | Voxel or image stacks per material; layer bitmaps | 3 |
| Directed energy deposition | NC programs on the machining stack | 3 |
| Sheet lamination | Cut paths plus machining programs | 5 |

**Decision D-MFG-11:** The additive pipeline slices the design Body directly in any representation, never through an STL, with an `ErrorBound` per slice.
*Why:* triangulating a dense lattice is the bottleneck of conventional build preparation, and direct slicing removes both the bottleneck and the facet error.
*Rejected:* mesh-only pipelines, which blow up memory and facet curved surfaces.

**Decision D-MFG-25:** Until Crucible's slicer passes its comparison, builds go as 3MF to the bureau's build-preparation software for GP2 (contract 13.1) or to the user's slicer. Filament-printer 3MFs carry plates, orientation, modifiers and settings, which PrusaSlicer reads [PrusaSlicer 3MF], as do OrcaSlicer [OrcaSlicer 3MF] and Bambu Studio [Bambu Studio CLI].
*Why:* incumbent build processors carry years of machine and material profiles that a new slicer cannot match on day one.
*Rejected:* Crucible's slicer first, which is unproven; linking an AGPL slicer, which contract 7.7 forbids.

A person's uncontrolled export to a local slicer is an audited local write, not an Act (contract 7.6). The bureau's file-acceptance test (contract 13.2) covers a Beam Lattice 3MF, a triangle 3MF and a sliced build. Devices lacking a required 3MF extension must refuse the file [3MF Core], and the Beam Lattice extension is one that a consumer may lack [3MF Beam Lattice], so GP2 may also ship as a mesh 3MF.

A 100 mm part with 2 mm cells has about 1.25 × 10⁵ cells, or 10⁸ triangles at 10 µm chordal error (estimate). GP2's mesh export therefore targets at most 2 × 10⁷ triangles in a 3MF under 500 MB, which bounds its lattice density. Its gate 3MF comes from the tagged run build (contract 13.1).

Crucible's slicer serves what only it does: direct slicing of implicit lattices and Field-driven infill. It becomes the default for filament printers only after matching the reference slicers on the thin-wall corpus and on print time. Binary G-code follows libbgcode's published format, without linking the AGPL code [libbgcode].

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

**Decision D-MFG-12:** 3D packing adopts spectral packing: FFT correlation of voxel grids for collisions, plus a translational removability check [Cui et al. 2023]. The correlation is `anvil::correlate_grids` with exact integer counts, fixed-point scores and ties broken by grid index.
*Why:* it is the best published trade-off between density and speed, and integer counts make placements bit-identical on every platform.
*Rejected:* bounding-box packers, which reach low density; floating-point FFT unchanged, whose argmin flips between platforms.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Orientation | `orient(part, printer, objectives, seed) -> [ParetoOrientation]` over support, height, critical faces, distortion, peel area and anisotropy | None: it reports the Pareto front and never picks without weights | MFG-O-AM-1 | 1 |
| Build hand-off | 3MF for a named slicer or the bureau's software; a mesh 3MF within GP2's budget where Beam Lattice fails | Unreadable settings and extensions listed | MFG-O-AM-2 | 1 |
| Plate nesting and 3D packing | Footprint nesting with the 2D nester; `pack(parts, volume, rules, seed, budget) -> Assembly`, interlock-free | `Infeasible` when a part exceeds the volume | MFG-O-AM-3 | 2 |
| Supports | Tree supports (extrusion); point supports with peel and island checks (vat); block, line, cone and lattice supports (metal powder bed) | Unsupported overhangs and islands, with fixes | MFG-O-AM-4 | 2 |
| Labels and serials | Engraved or embossed identifiers linked to `repo` serials | `Infeasible` when the face is too small | MFG-O-AM-4 | 2 |

## Slicing, lattices, process simulation and DfAM

A printed part's strength and shape depend on how the process builds it, so this section covers slicing, the as-built lattice data GP2's checks need, distortion and design-for-additive checks.

Variable-width perimeters follow Kuipers and colleagues [Kuipers et al. 2020], and curved layers the quaternion-field framework of Zhang and colleagues [Zhang et al. 2022]. PrusaSlicer [PrusaSlicer], OrcaSlicer [OrcaSlicer] and CuraEngine [CuraEngine] are AGPL-3.0, so they serve only as reference oracles. MFG checks MEC's lattices against printer limits and writes them without meshing.

### As-built struts for GP2

GP2's strut checks need as-built strut data in phase 1 (contract 13.4). A strut printed at 1 mm is not a 1 mm cylinder: down-skin surfaces carry adhered powder, the axis wanders, and nodes where struts meet accumulate material. The checks therefore read Materials and geometry measured on printed coupons, not nominal CAD.

**Decision D-MFG-41:** As-built strut calibration takes at least 18 strut specimens from three build plates for every GP2 strut diameter and build angle, per machine, alloy and parameter set. It measures diameter and its scatter, waviness over the radius of gyration, and single-strut tension and compression strength. CT scans of as-built unit cells from the same plates become implicit Bodies on which FLX fits node corrections, and the oracle holds out whole build plates.
*Why:* 18 specimens from three batches is the reduced-sampling minimum for a B-basis value under the Composite Materials Handbook [NPL MAT 134], which COV's phase 1 tolerance limits need, and cracks in GP2 start at as-built nodes that nominal cells do not represent.
*Rejected:* nominal-geometry node fits, which miss systematic node growth; fewer replicates with typical values, which leave strength reads without a statistical basis; a random specimen split, which leaks one plate's bias into both sides.

COV builds strut-scale Materials, their B-basis values and the strut imperfection regime variable from these data. GP2's struts are stocky, so compression is decided by a strut-strength check that reads MFG's compression tests: the localized axial stress against the as-built compressive strength, reduced by a factor computed from the measured waviness. Eigen-buckling stays for members slender enough for it to decide ([COV, Dynamics and stability](04-coverage.md#dynamics-and-stability)). The CT cells are segmented to implicit Bodies, so FLX's phase 1 immersed solver runs on them at full resolution.

### Distortion and compensation

Metal powder bed parts warp as each layer shrinks on the one below, and a build that comes off the plate out of tolerance is scrap.

**Decision D-MFG-13:** Distortion compensation inverts the simulated displacement Field and applies it to the build geometry with `anvil::deform`, iterating until the predicted shape is in tolerance.
*Why:* it is the contract's "Fields driving geometry" mechanism and leaves the design Body untouched.
*Rejected:* mesh morphing at export, which loses associativity and the B-rep.

FLX owns inherent-strain prediction, phase 2 in contract 13.4, as a declared sequence:

1. Layer-group activation of part and supports, the supports a homogenized lattice of calibrated stiffness.
2. Baseplate cut, then support removal.
3. Optional stress relief, which scales the inherent strain by a calibrated relaxation factor.

MFG supplies each step's data from coupons, such as cantilevers cut from the plate. Inherent strain lumps each layer's thermal history into a strain set calibrated on such coupons [Setien et al. 2019], so it holds only within its calibration. Phase 1 predicts no distortion for GP2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| DfAM checks | Wall and detail size from `anvil::thickness`, overhang, bridging, trapped powder or resin, drain holes, strut and wall thickness (1); thermal mass, slender features, support removal, allowance (2) | Located failures with fixes | MFG-O-AM-5 | 1, 2 |
| As-built strut calibration (metal powder bed) | Per machine, alloy and parameter set, every GP2 strut diameter and angle: at least 18 specimens from three plates; diameter and scatter, waviness, tension and compression tests; CT unit cells as implicit Bodies; held out by plate. Requires: COV Statistical basis (13.4) | `MissingData` for an uncalibrated diameter or angle; `InsufficientSamples` below the replicate count | MFG-O-AM-12 | 1 |
| Conformal lattices | Cells mapped by a parameterization | Cells above a distortion bound reported | MFG-O-AM-5 | 2 |
| Planar slicing | `anvil::section` per layer on any representation, with `ErrorBound` | Open contours name the faces | MFG-O-AM-6 | 2 |
| Extrusion and vat layers | Adaptive layer height, variable-width perimeters, Field-driven infill, seams and travel; anti-aliased masks | Regions thinner than a bead; `OutsideEnvelope` | MFG-O-AM-6 | 2 |
| Powder bed scan vectors | Hatch, stripes, islands and skins in 3MF Toolpath or another open format a named machine partner accepts | `Unsupported` without a partner format | MFG-O-AM-6 | 4 |
| Multi-material, deposition and curved layers | Per-region materials from Fields (3); bead paths on the machining stack (3); isosurface layers (4) | `MissingData`; `Collision`; `Infeasible` order | MFG-O-AM-6 | 3, 4 |
| Inherent-strain distortion | Coupon data for FLX's sequence: layer-group strains, support stiffness, relaxation factor. Requires: FLX Additive distortion sequence | `OutsideEnvelope` outside the calibrated set | MFG-O-AM-7 | 2 |
| Recoater risk and thermo-mechanics | Recoater clearance (2); deposition bead activation with plasticity (3); powder bed layer thermo-mechanics on COV's model (4) | `OutsideEnvelope` at melt-pool scale | MFG-O-AM-7 | 2, 3, 4 |
| Compensation | Iterative pre-deformation, sent as geometry to the vendor's build processor | `Infeasible` with the residual | MFG-O-AM-8 | 2 |
| Cure, sintering and warp | Vat working curve (2); binder-jet shrinkage and filament warp (4) | `MissingData` without constants; `OutsideEnvelope` | MFG-O-AM-9 | 2, 4 |

## Printers, 3MF and print transfer

A print job moves energy and hot metal like any machine program, so this section applies the same transfer rules to printers and defines the files they read.

Printer profiles are packages: the printer Assembly, parameter sets with envelopes, material profiles and calibration prints such as OrcaSlicer's [OrcaSlicer]. The 3MF suite is ISO/IEC 25422:2025 [3MF specifications], and its Toolpath extension is at 1.0.0 [3MF Toolpath].

Every printer is reached through the machine gateway, and reading its status is a Read. The phase 2 gate's extrusion part goes to an open-firmware printer through `send_print_job` (contract 13.1), and a maker iterating on a print uses a bench session rather than one Approval per upload.

Bambu Connect "removes slicing functions while enabling remote control and print initiation" [Bambu Lab 2025]. Its Developer Mode leaves MQTT, live stream and FTP open without vendor support [Bambu Developer Mode]. There `send_print_job` uploads over FTP only, where the printer's owner has enabled Developer Mode and recorded that choice in the printer's device record; otherwise a person starts the job in Bambu Connect.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| 3MF production write | Build items, object references, UUIDs, materials, beam lattices and thumbnails through ECO's writer | Unsupported constructs listed, never dropped | MFG-O-AM-10 | 1 |
| Further 3MF extensions | Boolean, Volumetric and Secure Content (3), and Toolpath once a machine partner accepts it (3), through ECO's writer | Written only where the target declares support | MFG-O-AM-10 | 3 |
| Binary G-code | bgcode from the published description | Unsupported blocks listed | MFG-O-AM-11 | 2 |
| Printer profiles and calibration | Profiles with envelopes; calibration prints and coupons | `OutsideEnvelope` outside the profile | MFG-O-AM-11 | 2 |
| Print transfer and control | `send_print_job` to OctoPrint, Moonraker and PrusaLink with start parameters fixed false, and to Bambu by Developer Mode FTP or Bambu Connect; bench sessions; `start_print`; cancellation | Never retried without a person; starts refused without contract 7.6's conditions | MFG-O-SAFE-2 | 2 |

## Moulds and injection moulding

GP5's moulded enclosure must come out of its tool within measured warpage, so this section covers designing the tool and simulating the fill, pack, cool and warp that decide it.

Tooling is designed in Ingot as Parts and Assemblies, the process runs as Flux forms, and results are Fields. MEC's `split_mold` returns core, cavity and side-action Bodies (phase 3), and MFG supplies the anisotropic shrink Field that sizes them.

**Decision D-MFG-14:** Tooling geometry derives from the part by Anvil operations and stays associative; tool-only edits (shutoffs, vents, cooling) are features on the derived Body.
*Why:* associativity is the main lever against late tooling changes, which are the costliest changes in moulding.
*Rejected:* exported tool geometry edited separately, which breaks the single model.

Filling a thin wall is nearly two-dimensional: the melt flows between two close walls, and the Hele-Shaw approximation averages across the gap. It answers thin-wall questions in seconds but fails where the flow becomes three-dimensional, at thick sections, steps and the flow front itself.

**Decision D-MFG-15:** `SignOff` fill, pack and cool run 3D octree solvers with a level-set flow front and eight cells across the half-thickness, and warpage carries a calibrated grid-convergence bound at measured points from two coarser grids built by octree coarsening. `Interactive` uses mid-surface Hele-Shaw within three regime variables: h/L_flow ≤ 0.1, |∇h| ≤ 0.1, and a distance of 2h from gates, rib roots, steps and the front.
*Why:* gap-averaged flow fails where fibre orientation and frozen layers form, Hele-Shaw answers thin walls in seconds, and coarsening from the production grid keeps solution verification cheaper than the solve it verifies.
*Rejected:* Hele-Shaw only, which is invalid for thick parts; 3D only, which is too slow interactively; refining above the production grid for verification, which multiplies the cost of a 3D transient solve.

Regions that fail the third regime variable are flagged and need the 3D model at `SignOff`. Phase 3 calibrates the thresholds on a step plate and a ribbed plaque; until then the zone is `Extrapolated`. GP5 at eight cells across a 1 mm half-thickness over 5 × 10⁴ mm² of wall needs about 5 × 10⁷ cells (estimate), and runs on a team server (target). The two coarser grids for the warpage bound hold about one eighth and one sixty-fourth as many cells, so verification adds roughly 15% to the solve (estimate). The bound itself is FLX's calibrated grid convergence index ([FLX, Error budgets, goals and checks](03-flux.md#error-budgets-goals-and-checks)).

**Decision D-MFG-29:** Short-fibre orientation uses the ARD-RSC model with a fitted closure [Phelps and Tucker 2009], with Folgar–Tucker as COV's L0 level. Warpage follows residual stress along the pvT path with frozen-layer pressure, mould constraint and crystallization kinetics.
*Why:* measured orientation evolves more slowly than Jeffery-based models predict [Wang et al. 2008], and pressure history dominates warpage.
*Rejected:* Folgar–Tucker alone; thermal shrinkage alone.

A short shot is a result, not an error: an unfilled-region Field with its frozen front. Non-convergence returns `Infeasible` with the last converged time.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Mouldability and pull direction | Draft, undercut, thickness and sink-risk Fields; directions ranked by undercut area and side actions | Located failures; ties reported | MFG-O-MOLD-1 | 3 |
| Parting, shutoffs, core and cavity | Parting line from silhouettes; ruled or extended surfaces; `split_mold` with MFG's anisotropic shrink Field | `Infeasible` with the open loop; `ResolveError` | MFG-O-MOLD-1 | 3 |
| Side actions, ejection and mould base | Slides and lifters with travel; ejector pins with force; standard plates as catalog parts | `Collision` during opening; pin overload | MFG-O-MOLD-2 | 3 |
| Gates, runners, cooling and venting | Gate type and location, runner balancing, Pareto gate search; drilled, baffled and conformal channels; vents at air traps | Unmet constraints; steel-distance violations; unvented traps | MFG-O-MOLD-2 | 3 |
| Fill, pack and cool | 3D level-set solver at `SignOff`, Hele-Shaw at `Interactive`, with COV's Cross–WLF and Tait pvT, gate freeze and cyclic mould conduction; calibrated grid-convergence bound on warpage at measured points. Requires: FLX Solution verification | `OutsideEnvelope` outside the melt range or Hele-Shaw regime; jetting out of scope | MFG-O-MOLD-3 | 3 |
| Fibre orientation, warpage and compensation | ARD-RSC orientation; residual-stress warpage; cavity pre-deformation by Field-driven compensation | `OutsideEnvelope` for long fibres; `Infeasible` when compensation stalls | MFG-O-MOLD-4 | 3 |
| Moulding variants | Gas-assist, co-injection, overmoulding, injection-compression, foaming | `Unsupported` until each variant's model is declared | MFG-O-MOLD-3 | 4 |

## Casting and bulk forming

Castings and forgings are designed for their process before they are simulated, so this section pairs rule-based design with physics that is honest about its limits.

Rule-based design (patterns, gating, risers) comes first; solidification comes from COV's physics package. High-pressure die-casting jets atomize at gate velocities beyond the model's reach, so above the breakup Weber number filling is `Extrapolated` (COV's out-of-reach record OOR-8). The Niyama criterion was validated on WCB steel, A356 and AZ91D [Carlson and Beckermann 2009], and porosity is predicted only for calibrated alloys.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Patterns, gating and risers | Pattern with shrinkage, draft and allowance Fields, cores; ingates from fill time and pressurization ratio; risers by modulus and feeding distance | Velocities above the ingate limit; `Infeasible` with the isolated hot spot | MFG-O-CAST-1 | 4 |
| Die-casting die and shot profile | Die halves, slides, overflows, vacuum vents, trim die; phases, switch-over, intensification | `OutsideEnvelope` beyond the machine | MFG-O-CAST-1 | 4 |
| Filling, solidification and die cycling | Free-surface filling with the Weber regime; enthalpy with fraction-solid curves; cyclic die steady state | `Extrapolated` above breakup; uncalibrated alloys refused | MFG-O-CAST-2 | 6 |
| Porosity and defect indicators | Dimensionless Niyama; air entrapment and cold shuts | `OutsideEnvelope` for uncalibrated alloys | MFG-O-CAST-2 | 6 |
| Investment casting and hot tears | Wax trees, shells, radiation cooling; solidification stress | `OutsideEnvelope` for directional and single-crystal growth | MFG-O-CAST-2 | 6 |
| Forging and extrusion | Preforms and dies with flash, load and die stress by rigid-viscoplastic FEM; extrusion dies by ALE flow | Laps and folds flagged; seam welds out of scope | MFG-O-BULK-1 | 5 |
| Thermoforming | Moulds with draft and vents; membrane thickness; trim programs | `OutsideEnvelope` outside the tested range | MFG-O-BULK-1 | 4 |
| Blow, rotational and compression moulding | Parison and preform design; deposition wall thickness; SMC and BMC charge and flow | Rotational results flagged indicative | MFG-O-BULK-1 | 5 |

## Sheet forming

Stamped and bent sheet parts fail by splitting, wrinkling and springback, and this section covers the tools and simulations that predict them; MEC owns sheet-metal design and MFG owns how sheet parts are made.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Tube bending | Rotary-draw sequence, tooling, collision, thinning, ovality; springback from measured tables | `Collision` or `Infeasible` with fixes | MFG-O-FORM-1 | 3 |
| Blank development and formability | One-step inverse FEM; incremental shell FEM for thinning, strains and forming-limit margin | `OutsideEnvelope` outside calibrated curves | MFG-O-FORM-2 | 5 |
| Die faces, stages and progressive dies | Binder, addendum, beads, trim and flange lines; stages with tonnage; strip layout | `ResolveError`; `Infeasible` naming the stage | MFG-O-FORM-2 | 5 |
| Springback, compensation and robustness | Unloading analysis; Field-driven compensation; capability Fields under variation | `OutsideEnvelope` without kinematic hardening | MFG-O-FORM-2 | 5 |
| Roll forming and hydroforming | Flower pattern and passes; pressure and feed paths with burst and wrinkle margins | Exceeded limits reported | MFG-O-FORM-2 | 5 |

## Welding, joining and composites

GP4's welded frame must come out within measured distortion, so this section covers weld procedures, sequences and distortion, along with fastening, bonding and laminate manufacture.

MEC owns weld joints, symbols and laminate design; MFG owns procedures, sequences, paths, distortion and laminate manufacture. Procedure records follow ISO 15609-1:2019, ISO 15614-1:2017 with Amd 1:2019 and ISO 9606-1:2012 [EVS welding], or AWS D1.1 and ASME IX. MEC's `Weld` quality level (ISO 5817 or AWS D1.1) drives inspection plans.

Weldment Parts carry MEC's `execution_class` under EN 1090-2:2018+A1:2024 [EVS EN 1090-2]. MFG derives the extent of non-destructive testing and the ISO 3834 quality-requirement part from it, and checks each `Weld`'s quality level against it. Phase 5 enforces it for GP8.

Inherent strain is the welding analogue of the additive method above: the shrinkage a weld leaves behind is lumped into an initial strain on a local model of the joint. A frame modelled as beams has no joint volume to carry it, so the strain acts through a small solid model of each joint.

**Decision D-MFG-32:** In frames Flux models as beams, weld shrinkage enters as joint loads from inherent strain on local joint models that `flux::mark_reduction` keeps solid. Phase 2 strains come from coupons per joint type, thickness, process and heat input.
*Why:* inherent strain is an initial strain in an elastic analysis of the joint [Murakawa et al. 2010], which a beam lacks.
*Rejected:* inherent strain applied to beams, where it is undefined; waiting for phase 4's transient model.

`tightening` picks torque-angle or yield-controlled tightening when MEC's preload range is narrower than torque control's scatter.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Weld procedures and pass plans | Procedure specifications linked to qualification records and welder records; heat input and pass plans; visual and non-destructive testing plans per quality level and execution class | `MissingData` for unqualified combinations; `OutsideEnvelope` | MFG-O-JOIN-1 | 2 |
| Weld sequencing and structure-scale distortion | Order and direction minimizing distortion and travel; inherent strain on shells or solids, joint loads on beams. Requires: FLX Weld joint loads on frames | `OutsideEnvelope` outside the coupons' heat input and thickness | MFG-O-JOIN-2 | 2 |
| Joint-scale weld simulation | Transient thermo-elasto-plasticity with a moving heat source [Goldak et al. 1984] calibrated by macrograph; phase transformation from COV's kinetics (contract 13.4) | Long runs flagged at `Interactive` | MFG-O-JOIN-2 | 4 |
| Robot weld paths | Torch angles, weaving and seam tracking | `Collision`, `Unreachable` | MFG-O-ASM-4 | 3 |
| Fastening specification | Method, target with scatter, sequence, tool and audit from MEC's preload range | `Infeasible` when scatter misses the range | MFG-O-JOIN-3 | 2 |
| Riveting, clinching and bonding | Fastener, pitch, edge distance and access; bead paths, bondline, preparation and cure | Rule failures; `MissingData` without adhesive data | MFG-O-JOIN-3 | 3 |
| Composite plates, plies and layup | Plate machining (3); MEC plies nested with grain and ordered, with projector data (4) | Missing ply references | MFG-O-JOIN-4 | 3, 4 |
| Automated fibre and tape placement and cure cycles | Courses within steering, gap and overlap limits; cure cycle on COV's model with spring-in | `Infeasible` beyond steering limits; `OutsideEnvelope` without kinetics | MFG-O-JOIN-4 | 5 |

## Surface and heat treatment

Coatings and heat treatment change a part's dimensions and properties after machining, so this section records them on the model where downstream checks can read them.

Treatments are typed records attached to faces through Queries, plus routing steps whose dimensional and property effects downstream checks read. COV owns transformation and quench physics; MFG owns specification, routing, masking, inspection and dimensional consequences. The bracket's hard anodize looks like this:

```
part.treat(anodize(type: hard, thickness: 50um ± 10um, seal: none))
    .mask(part.faces(threads) + part.face(mating))
part.heat_treat(solution_and_age(spec: shop::t6_6061), inspect: hardness(points: 3))
```

Hard anodize grows into the substrate as well as out of it, so the dimensional effect is a Field per face, and a fit check on a bore reads the coated size.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Coating specification | Process, standard, thickness `Tol`, colour, masking Queries, pre-treatment | Unknown standards; conflicting masks | MFG-O-TREAT-1 | 1 |
| Dimensional effect | Build-up per face as a Field, including substrate growth | `MissingData` without a growth ratio | MFG-O-TREAT-1 | 2 |
| Heat treatment and hot isostatic pressing | Recipes with hardness and case-depth targets (2); pressing and additive stress relief (3); distortion from COV's transformation models, compensated (6) | `OutsideEnvelope` when COV lacks the alloy | MFG-O-TREAT-2 | 2, 3, 6 |
| Plating, paint and powder coat | Film thickness, cure, masking and spray paths (4); plating current distribution from COV's package (5) | `OutsideEnvelope` for unmodelled chemistry | MFG-O-TREAT-1 | 4, 5 |

## Electronics and harness manufacturing handoff

A board or harness is made by a fabricator or contract manufacturer from files, so this section defines the packages MFG hands them and the rules that make those packages buildable.

MFG owns the factory hand-off: package choice, fabricator capability records and rule packs, panels, stencils, test strategy and the harness package. ELX owns the board model, its rule-check engine, the IPC-2152 current screen, `test_point` features, functional spacing and the coating record; ECO owns the writers. A board passes manufacturability checks for one specific fabricator and class. A harness's path from connector selection to formboard runs through three owners, and ELX walks through it in one place ([ELX, Wire harnesses](08-electronics-systems.md#wire-harnesses)).

**Decision D-MFG-16:** The default fabrication package is IPC-2581 revision C with Gerber X2 layers (revision 2026.05), XNC drill, the job file and an IPC-D-356 netlist. ODB++ from ECO's writer (phase 3) serves houses that read it, and ECO owns every writer.
*Why:* IPC-2581C is open and carries design-for-fabrication feedback [IPC-2581C], Gerber is the de facto standard [Ucamco Gerber], and fabricators test the bare board against a netlist.
*Rejected:* Gerber only, which carries no stackup or feedback; ODB++ only through a licensed translator, though an open tool writes it [KiCad 9.0].

Boards carry `fab_class` and `assembly_class` (Class 1, 2, 3 or 3/A), which select rule packs citing IPC-6012F, IPC-A-600M, IPC-A-610J and J-STD-001J [IPC store]. Via classes carry an IPC-4761 protection type (tented, plugged, filled or capped), which the fabrication drawing notes and a via-in-pad rule checks. The IPC-2581 consortium publishes the format openly [IPC-2581].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Fabrication package | Per fabricator: IPC-2581C, Gerber X2, XNC drill and route, job file, IPC-D-356, impedance and stackup tables, or ODB++, through ECO's writers | Unsupported constructs listed | MFG-O-PCB-1 | 3 |
| Assembly package | Placements, Gerber X3, assembly BOM with approved manufacturers, rotation conventions per line, drawings with ELX's coating keep-outs | `MissingData` without a rotation convention | MFG-O-PCB-2 | 3 |
| Classes, rule packs and fabrication drawing | Classes select annular ring, plating and acceptability rules; drawing notes for class, IPC-4101 material, finish, via protection, impedance and acceptance | A board without a class blocks the package | MFG-O-PCB-3 | 3 |
| Panels, stencils and reflow | Rails, tabs, V-score, fiducials, coupons, nested mixed panels, tab stress in Flux; stencil apertures by area ratio; reflow limits from paste and part ratings | `Infeasible` beyond line limits; apertures below ratio; `OutsideEnvelope` | MFG-O-PCB-4 | 3 |
| Fabrication and assembly rule checks | Rule packs on ELX's rule engine (annular ring, spacing, slivers, acid traps, copper balance, via-in-pad; part spacing, tombstoning, rework access); feedback records | Located failures with fixes | MFG-O-PCB-5 | 3 |
| Test access and programs | Coverage, probe spacing and fixture side; a Proposal adding `test_point` features; flying-probe and bed-of-nails data; boundary scan | Untestable nets, including points under coating | MFG-O-PCB-6 | 3 |
| Box build | Board Instances feed sequence planning and work instructions | `Infeasible` listing interlocked Instances | MFG-O-ASM-1 | 3 |
| Harness manufacturing package | 1:1 formboard from MEC geometry; connector face views with cavity numbers; cut list with gauge, colour and lengths; terminals and seals with crimp height and pull force; splices, markers, coverings; test netlist; IPC/WHMA-A-620F class | `MissingData` for terminals without crimp data | MFG-O-HARN-1 | 4 |

## Assembly and work instructions

A product is not made until it is assembled, so this section plans the order of assembly, checks that people and robots can do it, and writes the instructions they follow.

**Decision D-MFG-17:** Assembly planning is disassembly search over continuous collision-free motions, with gravity stability checked by Flux rigid-body contact, giving an AND/OR precedence graph.
*Why:* disassembly handles tight clearances and fasteners, and one graph feeds line balancing, instructions, repairability and recyclability.
*Rejected:* direction-cone heuristics, which fail on screws; hand-entered precedence, which is not regenerated when the design changes.

Robots are Machines that share kinematics, collision checking and posts with machine tools. Programs are proved in manual reduced-speed mode and never change safety-rated zones or speeds, as ISO 10218-1:2025 [EVS ISO 10218-1] and ISO 10218-2:2025 [EVS ISO 10218-2] require of the integrator. Each robot family's machine package states its file type and loading path; FANUC TP programs need the ASCII Upload option or compilation in Roboguide [RoboDK Fanuc].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Disassembly, sequences and fastening steps | `disassemble(assembly, seed, budget) -> PrecedenceGraph`; sequences minimizing reorientations and unstable states; fasteners as steps with tool and torque | `Infeasible` listing interlocked Instances; `MissingData` | MFG-O-ASM-1 | 2 |
| Tool and hand access | Swept volumes of tools and hands per step | `Unreachable` with fixes | MFG-O-ASM-1 | 3 |
| Design for assembly | `dfa(assembly) -> DfaReport`: separate-part test, handling and insertion difficulty after Boothroyd, Dewhurst and Knight [Boothroyd et al. 2011], efficiency index against the theoretical minimum time [DFMA DFA] | Instances without data listed as undetermined | MFG-O-ASM-2 | 2 |
| Work instructions | Steps with exploded views, tools, torques, checks and safety notes; glTF 2.0 with an accessible viewer and PDF (2); OpenUSD and locales (3) | Steps without a view; missing translations | MFG-O-ASM-3 | 2, 3 |
| Robot programming | Targets, external axes and positioners, collision-free seeded planning; posts to ABB RAPID, KUKA KRL, FANUC TP, Yaskawa INFORM and URScript [RoboDK post processors], never safety configuration; loading paths; cycle time | `Unreachable`; `kiln/work_limit`; `Unsupported`, including `AsciiUpload` | MFG-O-ASM-4 | 3 |
| Line balancing | Stations for a takt or takt for stations (3); mixed models, zoning, skills, two-sided lines (4) | `Infeasible` when a task exceeds takt | MFG-O-ASM-5 | 3, 4 |

## Inspection and measurement

A part is accepted on measurement, so this section turns the model's tolerances into characteristics, plans and decisions that account for measurement uncertainty.

MEC owns GD&T semantics and general tolerances ([MEC, Tolerancing](06-mechanical.md#tolerancing)); MFG owns measurement, evaluation and reporting. QIF is ISO 23952:2020 [ISO 23952] and DMIS is ISO 22093:2011 [ISO 22093]. A measurement is an Evidence record per characteristic check, pinned in `ingot.lock` under `[[evidence]]` by its `CheckId`, so one Change fixes every outcome that reads it (contract 5.6).

**Decision D-MFG-18:** Characteristics are first-class records generated from GD&T, with stable identities from provenance; untoleranced sizes take MEC's general tolerance, labelled "general". Plans, programs, results, SPC, first-article records and PPAP reference those identities.
*Why:* a design diff then names exactly which characteristics changed, which drives partial first-article inspection.
*Rejected:* balloon numbers as identity, which renumbering breaks; documents as the truth, which drift from the model.

**Decision D-MFG-26:** Balloon labels are allocated once per characteristic identity, never reused, and renumbered only on command. Each release produces the ballooned PDF that AS9102 Form 3, plans and reports cite.
*Why:* AS9102 revision C defines ballooned characteristics and documents [IAQG 9102C], and shops need labels that stay put across revisions.
*Rejected:* labels as identity; renumbering per release, which breaks open reports.

**Decision D-MFG-33:** Conformance decisions use the measuring lab's expanded uncertainty U: `Pass` inside the tolerance zone reduced by U, `Fail` outside the zone enlarged by U, and `Undecided` between. Phase 1 runs this for GP1 and GP2, with results from QIF 3.0 or a CSV keyed by balloon label.
*Why:* ISO 14253-1:2017 requires measurement uncertainty to count in conformance decisions [ISO 14253-1], and the phase 1 gate measures both parts.
*Rejected:* acceptance on the reading alone; waiting for phase 3's CMM work, which would leave the phase 1 gate without verdicts.

A customer PDF without a model imports as a controlled document whose balloons are placed by hand or by an agent Proposal. JCGM 100:2008 with Amendment 1 (2026), 101, 102 and 106 cover uncertainty, Monte Carlo propagation, multiple outputs and conformity [BIPM JCGM]. Inspection plans, gear plans among them, are written as QIF 3.0 Plans from phase 2; CMM path generation and DMIS output follow in phase 3.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Characteristics and balloons | Dimensions, controls, general tolerances, notes and special characteristics with stable labels: size, location, orientation, form and profile (1), the rest and foreign drawings (2) | Unresolved characteristics; label conflicts fail release | MFG-O-INSP-1 | 1, 2 |
| Results as Evidence records | QIF 3.0 Results or CSV by balloon label (1); DMIS from Crucible's CMM programs (3); one signed record per characteristic, pinned by `CheckId`. Requires: KLN Evidence records | Unmatched results reported | MFG-O-INSP-3 | 1, 3 |
| Conformance decisions | Guard-banded decisions with the lab's stated U | `Undecided` in the guard band; `MissingData` without U | MFG-O-INSP-5 | 1 |
| Inspection plans | QIF 3.0 Plans per characteristic with method and sampling, through ECO's writer | `MissingData` for a characteristic without a method | MFG-O-INSP-2 | 2 |
| Method selection and sampling | Method by uncertainty ratio and %GRR; point counts for a target uncertainty | `Infeasible` when no method meets the ratio | MFG-O-INSP-2 | 3 |
| CMM paths and programs | Collision-free paths with articulating heads; DMIS output; on-machine probing through posts | `Unreachable` points with fixes | MFG-O-INSP-2 | 3 |
| Feature evaluation | Least squares, minimum zone, inscribed and circumscribed fits; datum frames; tolerances on scans | `OutsideEnvelope` for thin coverage | MFG-O-INSP-4 | 3 |
| Scan registration and deviation | Robust or datum-constrained alignment; signed deviation Field with scanner uncertainty | Residual reported; gaps as regions | MFG-O-INSP-4 | 2 |
| Uncertainty budgets | Typed budgets with Flux sensitivities (2); JCGM 101 Monte Carlo and JCGM 106 guard bands (3); virtual CMM (4) | `MissingData` without error models | MFG-O-INSP-5 | 2, 3, 4 |

## Quality records: SPC, MSA, FAI and PPAP

Customers in regulated industries buy the records as much as the parts, so this section defines the first-article, nonconformance and process-capability records MFG keeps and how they join KLN's quality loop.

Process profiles declare Cp and Cpk per process and feature class, which MEC's default tolerance distribution reads. A first-article record signs the program revision that ran, the machine and part serials, and one passing Evidence record per characteristic. It moves a program to `Proven` (KLN owns the lifecycle; [KLN, Revisions and lifecycle states](05-kiln-repo-plm.md#revisions-and-lifecycle-states)), and AS9102 forms render it from phase 3. Per IAQG's summary of 9102 revision C, first-article inspection is not product acceptance and each item needs its own [IAQG 9102C].

A nonconformance record names serials, characteristics and a disposition. It arises from a failing measurement or from an edit at the control of a `Proven` or `Released` program, never from prove-out. A disposition to use nonconforming parts is a Waiver whose effectivity is a serial or lot range, which is what a deviation is (contract 5.6). From phase 3 a nonconformance links to KLN's corrective and preventive action record, which carries root cause, actions and an effectiveness check, so the loop from defect to verified fix closes inside Crucible. AIAG publishes PPAP-4 [AIAG PPAP] and the AIAG & VDA FMEA Handbook [AIAG-VDA FMEA].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Process capability profiles | Declared Cp and Cpk (2); computed from SPC data (3) | Unknown capability reported, never assumed | MFG-O-QUAL-1 | 2, 3 |
| First-article record | The program revision that ran, machine and part serials, one passing Evidence record per characteristic, signed; partial scope from the design diff | Missing or failing characteristics block it | MFG-O-QUAL-2 | 2 |
| Nonconformance | Records linked to serials, characteristics and dispositions, for failing measurements and for control edits of `Proven` or `Released` programs; use-as-is dispositions as Waivers with serial or lot effectivity; links to KLN's corrective actions (3) | A record without a disposition blocks the serials it names | MFG-O-QUAL-2 | 2, 3 |
| SPC | Control charts (X-bar, R, S, individuals, p, np, c, u, EWMA, CUSUM), run rules as data, capability indices with intervals; signals linked to machine, program and tool (4) | `MissingData` below the subgroup minimum | MFG-O-QUAL-1 | 3, 4 |
| Measurement system analysis | Gauge R&R by average and range and by ANOVA, bias, linearity, stability, attribute agreement | `MissingData` below the study design | MFG-O-QUAL-1 | 3 |
| AS9102 and partial first-article inspection | Forms 1 to 3 rendered from the first-article record, BOM, routing and certificates | Missing fields and unmeasured characteristics block the report | MFG-O-QUAL-2 | 3 |
| PPAP, FMEA and control plans | PPAP-4 elements with the retention matrix and customer overlays; process and design FMEA with action priority; controls and special-characteristic symbols linked to characteristics | Missing elements; uncontrolled special characteristics | MFG-O-QUAL-3 | 4 |

## Cost and sourcing

Cost decides most design trade-offs, so this section makes it a typed result of the actual process plan, with its basis and uncertainty shown.

Crucible costs the actual process plan where one exists and geometric proxies otherwise, so phase 1 costs GP1 by proxies and GP2 from its build.

**Decision D-MFG-19:** Cost is a typed roll-up over the process plan in `Money<C>` with a price date and an interval, painted as cost-density Fields. Each estimate states its basis: `parametric`, `planned` or `quoted`.
*Why:* one mechanism serves every process and shows both the basis and the costly features.
*Rejected:* a separate costing database, which drifts from the design; single numbers, which hide uncertainty; calling the basis a fidelity, which already means something else.

Cost elements are material, scrap, machine and setup time, labour, consumables, energy, tooling, overhead and logistics. Prices and rates are dated External inputs, and an amount payable rounds once through ING's `round_minor(currency)`. Supplier data leave a tenant only through AGT's Acts to KLN's recipient records. Where a product is made at more than one site, each site's routing carries its own cost.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Parametric cost | Regressions on geometric attributes per process family with stated training data and error | `OutsideEnvelope` outside the training range | MFG-O-COST-1 | 1 |
| Planned cost | `should_cost(part, routing, rates, qty) -> Cost` with `Money` per element, a total interval and a cost-density Field | `MissingData` for unknown rates; never an unflagged default | MFG-O-COST-2 | 1 (additive), 2 (machining, sheet, weld), 3 (moulding), 4 (others) |
| BOM roll-up and currency | EBOM query × item cost plus assembly labour; rates as dated External inputs | Items without cost listed; `Money<Eur> + Money<Usd>` fails to compile | MFG-O-COST-3 | 1 |
| Volume curves and target costing | Cost against quantity with tooling breakpoints; targets allocated down the BOM as checks | Failures name the largest contributors | MFG-O-COST-3 | 2 |
| Quote requests | `request_quote` Acts carrying a released package to ECO's partner connectors; quotes return as External inputs | Errors typed; never in evaluation | MFG-O-COST-4 | 2 |
| Suppliers and alternates | Processes, envelopes, materials, tolerances, certifications, capacity; matching to routing steps; form-fit-function alternates | Expired certifications; unchecked alternates blocked | MFG-O-SRC-1 | 2 |
| Make-or-buy, lead time and risk | Plan against quotes with risk and lead-time intervals; single source, geography, lifecycle and compliance per Instance | Missing data reported; unknown scores never low | MFG-O-SRC-2 | 3 |

## Factory connection and digital twin

The plan must reach the factory systems that schedule work and come back as data about what really happened, so this section connects machines, enterprise resource planning (ERP) and manufacturing execution systems (MES), and keeps per-serial records.

MTConnect's REST API is "read-only and does not produce any side effects" [MTConnect 2.5]. OPC 40501-1 (OPC UA for machine tools) is at 1.02.0 [OPC 40501-1], OPC 40001-3 (machinery job management) at 1.0.1 [OPC 40001-3], and async-opcua (MPL-2.0) links unmodified [async-opcua].

**Decision D-MFG-20:** Machine data enter through native MTConnect and OPC UA adapters outside evaluation, as External inputs signed by the gateway's device key. Both read, and OPC UA calls only the job allowlist, in `SIGNANDENCRYPT` sessions [OPC UA Part 4] with a site-managed certificate trust list.
*Why:* reads cannot move a machine, unsecured sessions let anyone call methods, and signed inputs keep evaluation deterministic.
*Rejected:* vendor protocols in the core, which belong in connectors; live data inside evaluation; OPC UA writes, since a write can start motion.

The gateway is `apps/machine-gateway`, owned by MFG and packaged by PLT (contract 12). It connects outbound only, runs connectors out of process behind its egress filter, and sits in an operational-technology zone designed after IEC 62443-3-3:2013 [IEC 62443-3-3]. It signs inputs with a TPM 2.0 key; without one its readings carry `data_untrusted` and serve no `SignOff` check.

A manufacturing BOM (MBOM) restructures the engineering BOM into what the factory builds: phantoms, kits, stations and consumables. Real products are often made in two plants, or by a contract manufacturer and an in-house line, each with its own MBOM, routings, programs and suppliers for one EBOM revision.

**Decision D-MFG-40:** MBOM rules, routings and work centres are keyed by (EBOM configuration point, `Site`), where a `Site` is KLN's policy-package record naming a plant or a supplier and its ERP mapping. Reconciliation, cost and ERP mapping run per site.
*Why:* one EBOM revision is routinely built at more than one site, and each site's plan must reconcile and cost on its own.
*Rejected:* one MBOM per product, which assumes a single factory; one design repository per site, which duplicates the EBOM.

Program Items already bind machine classes, so a second site with qualified machines needs no change to its programs. MFG maps MBOM, routings and work orders out through ECO's ERP and MES connectors from phase 2. Costs, lead times, inventory, status, scrap and labour return as External inputs. Manufacturing engineers restructure the MBOM in UIX's side-by-side EBOM and MBOM editor, whose drags write MBOM rule source ([UIX, Simulation, manufacturing, drawings and electronics](10-ui.md#simulation-manufacturing-drawings-and-electronics)). The digital twin is the design plus as-planned, as-run and as-measured records per serial.

[[DIAGRAM diagrams/07-manufacturing-factory-feedback.jsx: factory feedback loop · as-planned, as-run and as-measured back to the model]]

Read the loop clockwise: gateway readings become signed records, then per-serial comparisons, and only an approved calibration Proposal changes the model.

AOUSD announced OpenUSD Core Specification 1.0 on 17 December 2025 [AOUSD Core 1.0]; USD is an export target for factory cells, never the source of truth.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Gateway | `apps/machine-gateway`: outbound only, connectors behind its egress filter, safety functions in its core, TPM 2.0 key, offline buffering | Gaps recorded; readings `data_untrusted` without a TPM | MFG-O-FAC-1 | 2 |
| MTConnect and OPC UA adapters | MTConnect observations on axes, spindles, programs, tools and offsets; OPC UA Machine Tools and Machinery models with job orders mapped to routing steps | Schema and security-policy failures typed; partial data marked | MFG-O-FAC-2 | 3 |
| MES and ERP mapping | MBOM, routings and work orders out through ECO's connectors (2); status, scrap and labour back (4) | Mapping errors per field | MFG-O-FAC-3 | 2, 4 |
| MBOM and routings | EBOM-to-MBOM rules as Ingot (phantoms, kits, stations, consumables); routing steps with times and work centres (2); effectivity by serial, date, work order or lot (3) | Unconsumed items; unmapped work centres | MFG-O-FAC-4 | 2, 3 |
| Production sites | MBOM, routings and work centres keyed by (EBOM configuration point, `Site`); reconciliation, cost and ERP mapping per site | Reconciliation failure named per site | MFG-O-FAC-8 | 3 |
| OpenUSD export | Cells as USD layers with joints and prim paths from `EntityId`s, process animation (3); incremental layers (4) | Unsupported constructs listed | MFG-O-FAC-5 | 3, 4 |
| As-built records | Per serial: lots, revisions, operators, Waivers with serial effectivity, nonconformances, Evidence records, deviation Fields | Gaps flagged, never back-filled with nominal values | MFG-O-FAC-6 | 3 |
| Model calibration | As-run data update coefficients, cycle-time factors and distortion calibration through Proposals | Updates outside declared bounds need human approval | MFG-O-FAC-7 | 4 |
| Product twin export | As-built Assembly with measured Fields for FMI or SSP co-simulation | Missing measurements flagged as nominal | MFG-O-FAC-5 | 5 |

## Sustainability and compliance

Regulators now ask for a product's carbon, substances and passport, so this section derives each from the same model and process plan rather than from forms filled in by hand.

ISO 14044:2006, amended in 2017 and 2020 and confirmed in 2022, sets life-cycle assessment requirements [ISO 14044], and ISO 14040:2006 carries Amd 1:2020 [ISO 14040]. MFG computes cradle-to-gate inventory from the process plan and end of life from the disassembly graph.

The Ecodesign for Sustainable Products Regulation (ESPR), Regulation (EU) 2024/1781, has been in force since 18 July 2024 [EU ESPR], and Regulation (EU) 2026/1778 sets up the passport registry [EUR-Lex 2026/1778]. The registry opened on 20 July 2026, taking registration "through a web interface or an API" [Transition Pathways DPP]. Decision (EU) 2026/1736 references EN 18216 and EN 18219 to 18223 [EUR-Lex 2026/1736], and ESPR's Article 10(4) requires an independent back-up copy of each passport.

**Decision D-MFG-21:** The Digital Product Passport is generated from the released model, as-built records and life-cycle assessment, with each delegated act a versioned query mapping. `publish_passport` publishes to the economic operator's chosen service and mirrors a back-up to an independent provider; Crucible runs no passport service.
*Why:* requirements differ per product group, content must trace to the model, and ESPR requires the back-up.
*Rejected:* one hard-coded schema; manual forms, which drift; a Crucible-run service, which would hold records outside their tenants.

Regulation (EU) 2017/821 "will only apply directly to EU-based importers of tin, tantalum, tungsten and gold" [EU conflict minerals], so MFG checks 3TG sourcing data for completeness only. Regulation packages carry dated lists [ECHA Candidate List]. Substance checks return an ordinary `CheckOutcome`: unknown content is `Undecided { MissingData }`, never compliant, and a missing declaration fails release unless a Waiver covers it (contract 5.6).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Embodied carbon | Global warming potential per BOM line from COV's `EnvironmentalRecord`s (generic factors from phase 2), as per-Instance and density Fields; supplier data override | Generic against specific data flagged | MFG-O-SUST-1 | 2 |
| Life-cycle scope and inventory | Typed functional unit, boundary and allocation; flows from materials, power, consumables, scrap and transport | Missing scope fails to compile; flows without factors never zeroed | MFG-O-SUST-1 | 3 |
| Impact, hotspots and uncertainty | Factor packages with pinned versions (EF datasets, or ecoinvent under licence [ecoinvent]); contributions; Monte Carlo (4) | Unlicensed datasets unavailable, never substituted | MFG-O-SUST-2 | 3, 4 |
| Recyclability and repairability | Recoverable mass per stream from the disassembly graph; contaminating joints; access to service parts | Unlisted materials unrecoverable; `Unreachable` | MFG-O-SUST-3 | 3 |
| Passport mapping and identifiers | Delegated-act elements mapped to queries; identifiers per model, batch or item; carriers; public, professional and authority views | Unmapped elements block publication | MFG-O-DPP-1 | 3 |
| Registration and back-up copy | Registration through the Commission's API inside `publish_passport`, keeping the proof; each passport mirrored to the independent provider | Rejections typed; fails unless both copies succeed | MFG-O-DPP-2 | 3 |
| Battery passport | Battery Regulation elements for GP6's pack, required from 18 February 2027 for LMT, industrial above 2 kWh and EV batteries [EU Battery Regulation] | Unmapped elements block publication | MFG-O-DPP-1 | 4 |
| RoHS, REACH and SCIP | Ten RoHS substances at 0.1%, cadmium at 0.01%, per homogeneous material [EU RoHS], with the four phthalates added by Directive (EU) 2015/863 [EU 2015/863], from COV's declared substances; Candidate List, Annex XVII and SCIP data; IPC-1752C declarations | `Undecided { MissingData }` for unknown content, never compliant | MFG-O-REG-1 | 3 |
| 3TG sourcing data | Smelter lists and due-diligence records collected for reporting | `MissingData` for incomplete records; no compliance verdict | MFG-O-REG-2 | 3 |
| Other regimes | Packaging, batteries, WEEE [EU WEEE], TSCA [EPA TSCA] and Proposition 65 as regulation packages | `Undecided { MissingData }` for unknown content | MFG-O-REG-1 | 4 |

## Reference

### Failures

Every `MfgError` variant renders as `mfg/<snake_case>` (contract 7.6), and every `fixes` list holds typed edits ranked by how little they change. A reached search budget is not an `MfgError`: it is `kiln/work_limit` with the best result so far beside it (contract 7.2).

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
    MachineModel        { check: MachineCheck, fixes: Vec<Fix> },   // ChainOpen | TravelMismatch | HomeCollision | KinematicParameters
    OffsetMismatch      { register: OffsetRef, expected: Length, read: Length, tolerance: Length },
    ControllerVersionUnqualified { machine: MachineSerial, version: ControllerVersion, qualified: VersionRange },
    PlanUnapproved      { digest: ObjectId },
    HashMismatch        { diff: ObjectId },       // the semantic NC diff
    ProgramSlotOccupied { number: ProgramNumber, foreign: bool },
    DncSessionPreArmed  { machine: MachineSerial },
    GatewayUnreachable  { machine: MachineSerial },
}
```

### Controller capability flags

Posts read capability flags, never vendor names. The codes below come from each maker's documentation: Fanuc [Fanuc CNC], Siemens [Siemens Sinumerik], Heidenhain [Heidenhain TNC] and Haas [Haas G-codes].

| Capability flag | Fanuc | Siemens Sinumerik | Heidenhain TNC | Haas |
| --- | --- | --- | --- | --- |
| Tool centre point control | G43.4 / G43.5 | TRAORI | M128 or FUNCTION TCPM | G234 |
| Tilted work plane | Tilted Working Plane function | CYCLE800 | PLANE functions | G268 |
| High-speed contour mode | G05.1 Q1 | CYCLE832 | Cycle 32 TOLERANCE | G187 |
| Drilling cycles | G81 to G89 | CYCLE81 to CYCLE89 | Cycle 200 series | G81 to G89 |
| Parametric programs | Macro Executor | R parameters, GUD variables | Q parameters | Macro variables |

### Packages, WIT worlds and Rust homes

| Kind | Names |
| --- | --- |
| Ingot packages | `std::mfg::core`, `machining`, `modify`, `am`, `molding`, `casting`, `forming`, `joining`, `treatment`, `electronics`, `assembly`, `inspection`, `cost`, `sourcing`, `factory`, `sustainability` |
| WIT worlds in `crucible:mfg` | `toolpath-strategy`, `post-processor`, `nester`, `packer`, `slicer`, `recognizer`, `nc-interpreter` |
| Wasm components under `std/mfg/` | Strategies, the post engine, the 2D nester, the 3D packer, slicers, recognizers, the product NC interpreter |
| Operation families in `flux-op-*` (with FLX) | `flux-op-hele-shaw` (mid-surface filling), `flux-op-chatter` (zero-order and semi-discretization lobes) |
| Apps | `apps/machine-gateway` (MFG, packaged by PLT) |

## State of the art

All numeric goals in the last column of both tables are targets.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| High-efficiency roughing | Constant engagement; varied trochoids [Li et al. 2025] | Mastercam Dynamic Motion [Mastercam]; Fusion 3D Adaptive Clearing [Fusion adaptive]; hyperMILL [hyperMILL]; NX CAM [NX CAM] | Engagement-limited offset clearing unconditionally; the design-around adaptive spiral after counsel's opinion (D-MFG-35, D-MFG-7) | Cycle time within 3% of the best at equal engagement; zero bound violations |
| 3-axis finishing | Drop- and push-cutter [OpenCAMLib] | ModuleWorks 3-axis [ModuleWorks] | `tool_contact` on exact B-rep | Scallop and gouge error on analytic surfaces; throughput at least OpenCAMLib's |
| Collision and NC verification | Continuous collision detection on posted code; the controller maker's virtual kernel [NX VNCK] | ModuleWorks 5-axis [ModuleWorks]; VERICUT [VERICUT]; NX CAM with Sinumerik's kernel | Posted text under declared semantics, a vendor kernel at `SignOff` where licensed; certified gouge distance (D-MFG-23, D-MFG-37) | Zero false negatives per family; time per 1,000 blocks; differential agreement with the vendor kernel |
| Material removal | Adaptive GPU tri-dexel [Ozcan et al. 2024] | ModuleWorks; VERICUT | Narrow-band stock (D-MFG-6) | Volume error against exact Booleans; 60 fps scrubbing of 10⁶ blocks |
| Feeds and speeds | Mechanistic force models with constrained optimization | CloudNC [CloudNC CAM Assist]; VERICUT Force [VERICUT Force] | Source-labelled defaults, calibrated optimization (D-MFG-27) | Cycle time within 5% of the leader, zero violations |
| Chatter | Zero-order, multi-frequency and semi-discretization [Altintas et al. 2008] | CUTPRO [Altintas et al. 2008] | Zero-order at `Interactive`, semi-discretization at `SignOff` (D-MFG-10) | Published lobes; time-domain reference |
| Posts | Configurable controller posts | NX Post Configurator, ModuleWorks posts [ModuleWorks] | One engine with Ingot hooks, restart points and qualification (D-MFG-5, D-MFG-31) | Re-interpretation; conformance and qualification corpora |
| Target recognition | Panoptic graph segmentation on B-rep [FeatureFox] | AAGNet [AAGNet] | Design semantics, then rule and learned recognizers (D-MFG-34) | MFInstSeg panoptic quality at least 97%; above 0.9 with 250 parts |
| AI-assisted programming | Proposals with human review | CloudNC; NX suggestions [Janus NX 2606] | Agents on branches, Approval of the program subject (D-MFG-4) | Unedited approvals on held-out parts; zero bypasses |
| 2D nesting | Sparrow [Gardeyn et al. 2025] | Sparrow, jagua-rs [sparrow] | Adopt with deterministic budgets (D-MFG-9) | Within 1 point of sparrow's density at equal wall-clock time |
| 3D packing | Interlock-free spectral packing [Cui et al. 2023] | Netfabb [Cui et al. 2023]; Magics [Materialise Magics] | Integer counts (D-MFG-12) | Thingi10K: within 2 points at equal GPU time |
| Slicing | Direct slicing; variable-width beads [Kuipers et al. 2020]; tree supports [OrcaSlicer] | OrcaSlicer, PrusaSlicer | Hand-off first (D-MFG-25); direct slicing (D-MFG-11) | Thin-wall fill and print time no worse; 10× less memory on lattices |
| Multi-axis slicing | Quaternion-field curved layers [Zhang et al. 2022] | The paper's BSD-3-Clause code [S3-Slicer code] | Adopt in phase 4 | Support-free coverage and collision-free order on the paper's models |
| Lattices | Implicit, Field-driven lattices | nTop [nTop] | MEC lattices checked and written without meshing; as-built strut and node data (D-MFG-41) | Relative density error under 1% |
| Powder bed distortion | Inherent strain set from coupons [Setien et al. 2019] | Magics with Ansys [Materialise Magics]; Fusion [Fusion Manufacturing Extension] | FLX's declared sequence; Field-driven compensation (D-MFG-13) | AM-Bench bridge deflection within 10% [NIST AM-Bench 2018]; GP2 within 0.1 mm |
| Injection moulding | 3D non-isothermal flow; ARD-RSC [Phelps and Tucker 2009] | Moldflow [Moldflow] | 3D at `SignOff` with a grid-convergence bound, Hele-Shaw at `Interactive` (D-MFG-15, D-MFG-29) | Bay and Tucker's disk [Bay and Tucker 1992]; GP5 warpage within 20% |
| Casting | Filling, solidification, dimensionless Niyama [Carlson and Beckermann 2009] | MAGMASOFT [MAGMASOFT] | COV's solidification package, calibrated alloys only | WCB plate porosity; Stefan problem |
| Sheet forming | Incremental shell FEM with compensation | AutoForm [AutoForm] | Flux shells, Field-driven compensation | NUMISHEET 2014 springback benchmark [NUMISHEET 2014] |
| Weld distortion | Inherent strain [Murakawa et al. 2010]; moving-source transient [Goldak et al. 1984] | SYSWELD [SYSWELD] | Both by envelope; joint loads on beams (D-MFG-32) | GP4 distortion in band; NeT TG1 plate [NeT TG1] |
| Assembly planning | Assembly by disassembly [Tian et al. 2022] | The same method (research) | Adopt with deterministic search (D-MFG-17) | The paper's benchmark; 80 parts under 5 minutes |
| Line balancing | BB&R [BB&R] | BB&R | Adopt | All 269 instances optimal, mean under 1 s |
| Robot offline programming | Redundancy-resolved collision-free planning | RoboDK [RoboDK]; Process Simulate [Process Simulate] | Robots as Machines sharing CAM kinematics and posts | Re-interpreted motion; cycle time within 10% |
| Inspection | Model-based QIF plans [ISO 23952]; GUM and JCGM 101 [BIPM JCGM] | ZEISS CALYPSO [CALYPSO]; PolyWorks Inspector [PolyWorks] | Provenance identities, stable balloons, uncertainty-aware decisions (D-MFG-18, D-MFG-26, D-MFG-33) | QIF round trip; JCGM examples reproduced |
| Should-cost | Process-model cost from CAD [aPriori] | aPriori | Cost from generated plans, basis labelled (D-MFG-19) | Held-out quotes inside the interval for 90% of parts |
| Machine connectivity | MTConnect 2.5 [MTConnect 2.5]; OPC 40501-1 [OPC 40501-1] | MTConnect C++ reference agent [cppagent] | Read adapters, allowlisted job management, signed inputs (D-MFG-20) | Conformance against reference agents and servers |
| PCB hand-off | IPC-2581C with feedback [IPC-2581C]; Gerber 2026.05 [Ucamco Gerber downloads] | Valor NPI [Valor NPI] | IPC-2581C default package (D-MFG-16) | 1 µm XOR against independent readers; seeded-defect boards |
| Life-cycle assessment | ISO 14040 and 14044 process LCA [ISO 14044] | openLCA [openLCA]; SimaPro [SimaPro] | Inventory from actual process plans | Mass balance; reference product systems |

Parity with the incumbents. Each row names a documented incumbent feature and where Crucible matches or passes it. No AI-built clone named in contract 7.7 documents CAM, NC verification or shop-floor transfer, so no clone row applies yet.

| Capability | Incumbent and documented feature | Crucible's row and phase | Status |
| --- | --- | --- | --- |
| Toolpath trimming | Fusion trims a milling toolpath by polygon, plane or boundary and gouge-checks added links [Fusion trim] | Toolpath editing, 2 | Ahead: the trim is source keyed by pass, so it survives the next design change |
| Deleting passes | Fusion deletes selected passes or segments [Fusion delete passes] | Toolpath editing, 2 | Ahead: deletions resolve by pass key and fail typed when the pass disappears |
| High-efficiency roughing | Fusion 3D Adaptive Clearing [Fusion adaptive]; Mastercam Dynamic Motion [Mastercam] | Engagement-limited offset clearing, 2; adaptive clearing, 2 after counsel | Equal: the same measurable engagement bound, checked by an independent oracle |
| Controller-exact simulation | NX CAM runs Sinumerik's virtual NC kernel [NX VNCK] | Vendor controller kernels, 3 | Later: declared semantics serve from phase 2, the vendor kernel joins in phase 3 under the customer's licence |
| NC verification of posted code | VERICUT verifies posted programs [VERICUT] | Machine collision and clearance, 2; External NC verification, 2 | Ahead: verification is CI on every Change, and its verdicts are part of what the approver signs |
| Machine models | NX CAM simulates the machine and process [NX VNCK] | Machine package builder, 2; machine templates, 2 | Equal: packages are checked against the control's stored kinematic parameters |
| Moulding simulation | Moldflow fill, pack, cool and warp [Moldflow] | Fill, pack and cool, 3 | Equal, with a stated warpage bound at measured points |
| Forming simulation | AutoForm forming and springback [AutoForm] | Blank development and formability, 5 | Later: sheet forming waits for phase 5 (contract 13.4) |
| Casting simulation | MAGMASOFT [MAGMASOFT] | Filling, solidification and die cycling, 6 | Later: casting simulation waits for phase 6 (contract 13.4) |
| Weld distortion | SYSWELD [SYSWELD] | Weld sequencing and structure-scale distortion, 2; joint-scale weld simulation, 4 | Equal at structure scale in phase 2 |
| Build preparation and distortion | Magics [Materialise Magics]; Fusion Manufacturing Extension [Fusion Manufacturing Extension] | Build hand-off, 1; inherent-strain distortion and compensation, 2 | Equal: phase 1 hands builds to the bureau's own software |
| Quality records | Windchill ships CAPA, nonconformance, customer-experience and audit modules [Windchill quality] | Nonconformance, 2; KLN's corrective actions, 3 | Equal from phase 3: nonconformances link to KLN's corrective actions |
| Model-based inspection | ZEISS CALYPSO [CALYPSO]; PolyWorks Inspector [PolyWorks] | Inspection plans, 2; CMM paths and programs, 3 | Later for CMM programs; ahead on decisions, which count the lab's uncertainty |
| Should-cost | aPriori [aPriori] | Planned cost, 1 to 4 | Equal, costed from the actual plan with its basis labelled |
| Robot offline programming | RoboDK [RoboDK]; Process Simulate [Process Simulate] | Robot programming, 3 | Equal: robots share the machine-tool kinematics, posts and transfer rules |
| PCB manufacturing hand-off | Valor NPI [Valor NPI] | Fabrication and assembly rule checks, 3 | Equal, with rule packs per fabricator and class |

## Platform notes

- **Identical features.** Strategies, nesting, slicing and simulations are Wasm components or core Rust, so every platform runs the same code.
- **Determinism.** Programs, nests and slice contours are canonical results, so NC text is identical on every Tier 1 platform in the canonical platform class. `correlate_grids` is `Certified` with exact integer counts, and the GPU tri-dexel cache only renders.
- **Browser memory.** Stock grids, voxel grids and large nests stream in tiles. Evaluations above PLT's thresholds move to the heavy worker or a server, and the UI says so.
- **Machine access.** Devices are reached through the gateway, since Web Serial is not Baseline [MDN Web Serial]. MTConnect, OPC UA and DNC never run inside evaluation.
- **Controller files.** Line endings, character sets, lengths, sizes, names and storage normalizations belong to the `Controller` record; the platform layer writes posted bytes unchanged.
- **Vendor kernels.** A controller maker's kernel runs only where an External Op host supports its image; desktops may run it locally as `Unverified` at `Interactive` (contract 7.8).
- **Air-gapped shops.** Machine, tool, printer, material and regulation packages install offline through KLN's bundles (phase 3); results state the date of every External input.
- **Tier 2.** Tablets view programs, simulations and results; they approve physical-effect Acts only with an allowlisted roaming security key, and phones never approve them (contract 7.6).
- **Licensing.** PrusaSlicer, OrcaSlicer, CuraEngine, libbgcode, KiCad and OpenCAMLib are external references only. Sparrow, cavalier_contours, i_overlay [i_overlay], Clarabel.rs and Manifold [Manifold] are permissive, Clipper2 is BSL-1.0 [Clipper2], and jagua-rs and async-opcua are MPL-2.0 under contract 7.7.

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| All tabs | `std::mfg` packages (Reference lists them) | Ingot packages | 0 |
| MEC | Process profiles (Cp, Cpk, accepted representations); DfAM, manufacturability and assembly checks; cost models | `Check`, `Field`, packages | 1; 2 (Cp and Cpk, assembly checks) |
| MEC | Characteristic identities and balloon labels | Records | 1 |
| MEC | Press-brake allowance data; in-process drawings; the harness manufacturing package | Packages, drawings | 2; 4 (harness package) |
| FLX, COV | As-built strut calibration (diameter, waviness, tension and compression tests, CT unit cells) | `Field`, `Body`, packages | 1 |
| FLX, COV | Process profiles for manufacturing-constraint forms; coupon data for inherent strain and weld joints; process data under the material-or-process ownership rule | `Field`, packages | 2 |
| FLX | The Hele-Shaw filling and stability-lobe operation families | `flux-op-*` crates | 3 |
| ELX | Fabricator capability records (`fab::…`: laminates, via spans, spacing and HDI limits); rule packs by class; package choice; panels, stencils, test programs; fabrication feedback | `Check`, packages | 3 |
| KLN | Program subjects as `ItemDefinition`s of program Items; first-article and run records; setup sheets, instructions and inspection plans | CAS objects, records | 2 |
| KLN | MBOM rules and routings per `Site`; nonconformance records linked to corrective actions; as-built records | Records | 2; 3 (sites, corrective-action links, as-built records) |
| AGT | Typed physical-effect payloads with the approval page's fields; bench-session payload kinds; `request_quote` and `publish_passport` payloads; `MfgError` fixes | Act plans | 2; 3 (`publish_passport`) |
| UIX | Toolpaths with pass keys, stock, collisions, NC text with `BlockMap` and compensation modes, setup sheets, toolpath edits as source | `Body`, `Field` | 2 |
| UIX | DfAM and carbon Fields, cost lines | `Field`, records | 1; 2 (carbon) |
| ECO | `verify_nc`; `crucible:mfg` worlds; connector manifests with endpoint allowlists; machine-definition formats to list | WIT interfaces, packages | 2 |
| PLT | `apps/machine-gateway` for packaging | App | 2 |

## Oracles

Oracles live in `oracles/mfg/`, which agents read but never write; held-out parts, programs, nests and measurements are never shown to builders. Changing a pass criterion is a protected oracle change (contract 5.4).

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| MFG-O-CORE-1 | Records and fixes | Every artifact is a Body, Field, Assembly or plain value; every seeded failure carries a fix that clears it or says why not |
| MFG-O-CORE-2 | Outside data | Every External input and Evidence record read is pinned in `ingot.lock` and appears by `ObjectId` in its `CheckOutcome` |
| MFG-O-CORE-3 | Toolpath storage and pass keys | 10⁷ moves under 400 MB (target); single moves addressable for display; pass keys identical after a dimension edit that keeps the passes |
| MFG-O-CORE-4 | Representations | Seeded fallback regions release only for accepting processes or after conversion in tolerance; PMI on one fails |
| MFG-O-DET-1 | Determinism | Identical programs, nests, builds and reports on every Tier 1 target; "continue" never worsens a result |
| MFG-O-LABEL-1 | Label invariance | GP1 to GP3 plans and costs identical after re-randomizing every name |
| MFG-O-SAFE-1 | Subjects and changes | Edits inside a subject void Approvals, a changed setup sheet included; rebases, pocket changes, a controller update with an unchanged semantics digest, and a post release that keeps the canonical hash do not; orders touching EBOM definitions rejected; a part change returns exactly its dependent programs, legacy ones included; `Proven` refused while the revision that ran is unmerged |
| MFG-O-SAFE-2 | Transfers and starts | Unapproved, forged, mismatched, phone-approved and unconfirmed requests refused 100%; Approvals by credentials younger than 24 hours refused; bench-session transfers outside their lineage, count or expiry refused; `start_print` refuses profile-only declarations, non-extrusion printers and remote confirmations; programs survive simulator round trips, single-token edits never do |
| MFG-O-SAFE-3 | No start on the wire | Under wire capture against real servers or simulators (OctoPrint, Moonraker, PrusaLink, URSim, controls), no request carries a start or non-allowlisted method, and devices stay idle |
| MFG-O-SAFE-4 | Offsets and edits | Seeded offset mismatches blocked 100%; post-transfer edits alarm within 5 s; edit sessions yield exact diffs; a captured edit of a `Prototype` program opens a Proposal and a prove-out log entry with no nonconformance, and one of a `Released` program opens a nonconformance |
| MFG-O-SAFE-5 | DNC | Every injected feed fault stops and reports; controls waiting for data at commit receive zero bytes in 100% of cases |
| MFG-O-SAFE-6 | Program registry | Seeded collisions with foreign programs refused 100%; later revisions of the same Item replace their slot |
| MFG-O-SAFE-7 | Self-approval | A preparer's approval of their own transfer is refused while `self_approve_transfer` is off and accepted with AAL3 when it is on; every self-approved transfer appears in the audit log; the policy cannot be enabled without a signed widening Cedar change |
| MFG-O-KIN-1 | Kinematics | `fk` against a screw-theory implementation on 10,000 poses under 10⁻¹² m; `fk(ik(p))` equals `p` within 10⁻⁹ |
| MFG-O-KIN-2 | Singularities and limits | No unreported branch flip; tip deviation, axis derivatives, power and torque under bounds |
| MFG-O-KIN-3 | Machine packages | The reference shop's machines, built from STEP and specification sheets, reproduce the controls' stored kinematic parameters within 0.01 mm and the captured crash corpus; seeded open chains, travel mismatches and home collisions fail typed |
| MFG-O-POST-1 | Posts | An independent interpreter reproduces each program; family corpora match vendor simulators and reference-shop controls |
| MFG-O-POST-2 | Hooks | Golden posted files per configuration and hook set |
| MFG-O-POST-3 | Qualification | Reference programs equal the shop's proven ones modulo the declared list; captured corpus traces match `MotionSemantics` within tolerance, for reference-shop and shop-qualified captures alike; an unqualified controller version blocks transfer until recapture |
| MFG-O-POST-4 | Diff and block map | Self-diff empty; known edits found; every block maps to a toolpath point |
| MFG-O-TOOL-1 | Tools | Package round trip within 1 µm; gauge length equals the analytic stack-up; conflicting entries fail |
| MFG-O-TOOL-2 | Tool life | Predicted changes within ±25% of as-run counts (target) |
| MFG-O-STOCK-1 | Stock | Removed volume equals swept volume within the bound; rest plus part covers stock; exact hand-off transforms |
| MFG-O-SETUP-1 | Setup sheets and in-process drawings | Tombstone corpus verified per offset; offsets, program number, restart points and every tool appear once; in-process drawings match the hand-off Body and list every in-process characteristic |
| MFG-O-SETUP-2 | Jaws and probing | Parts seat without interference; probe paths collision-free |
| MFG-O-SETUP-3 | Fixtures | Rank tests on 3-2-1 cases; equilibrium and deflection in tolerance; access clear |
| MFG-O-MILL-1 | 2.5D and rest | No material above floor plus allowance; rest Body empty after the pass |
| MFG-O-MILL-2 | Engagement | An independent stock simulator keeps engagement and chip thickness under bound plus tolerance, for offset clearing, adaptive clearing and trochoidal slotting alike |
| MFG-O-MILL-3 | Finishing | Scallop Field under target; certified gouge check passes |
| MFG-O-MILL-4 | Edges, threads, holes | Chamfer size, thread profile, hole depth and position on simulated stock |
| MFG-O-MILL-5 | 5-axis | Wall deviation in tolerance; collision passes; axis smoothness bounds hold |
| MFG-O-TURN-1 | Turning | Revolved profile equals the part; simulated profile within allowance |
| MFG-O-TURN-2 | Multi-channel | Collision-free schedules honouring synchronization; optimal on small instances |
| MFG-O-EDM-1 | EDM | Kerf and ruled surfaces in tolerance; electrode plus gap reproduces the cavity |
| MFG-O-GEAR-1 | Gear cutting | Simulated flanks within the ISO 1328-1 grade on MEC's record; ground profiles within allowance |
| MFG-O-GEAR-2 | Gear inspection | Plans evaluate the design flank on reference gears; QIF Plans validate against the schema |
| MFG-O-CUT-1 | Profile cutting | Kerf, taper, bevel and punched sheet match the part; tour against a lower bound; the generic post reproduces the paths |
| MFG-O-CUT-2 | Flat-pattern hand-off | Every entity mapped per convention; re-import equals the flat pattern |
| MFG-O-CUT-3 | Press brake | Bends collision-free; optimal on small instances; bend-sheet values equal the plan |
| MFG-O-NEST-1 | Nests | Exact overlap and containment checks; remnant plus parts plus kerf equals the sheet; warm starts never worsen; ESICUP density within 1 point of sparrow at equal wall-clock time on the reference laptop |
| MFG-O-FEED-1 | Cutting data | Labels match sources; coefficients reproduce calibration cuts within uncertainty |
| MFG-O-FEED-2 | Constraint check | Spindle power within 10% of spindle-load data (target); no missed violation on recomputation |
| MFG-O-FEED-3 | Optimization | Zero violations; cycle time within 5% of the leader |
| MFG-O-CHAT-1 | Stability | Published frequency responses and lobes; time-domain agreement; recorded chatter flagged |
| MFG-O-SIM-1 | Gouges | Every planted gouge found with its depth, including wear values outside `wear_range` |
| MFG-O-SIM-2 | Collision | Ordinary and controller-semantics crash corpora detected 100% per family; undeclared semantics never pass |
| MFG-O-SIM-3 | External NC | Hand-written, third-party, macro-calling and probe-branching programs with planted crashes detected or `Undecided`, never passed |
| MFG-O-SIM-4 | Cycle time | Within 5% of measured after calibration (target) |
| MFG-O-SIM-5 | Viewer | Visual regression Snapshots under a fixed `RenderProfile` |
| MFG-O-SIM-6 | Restarts | Every restart entry collision-free; seeded restarts that skip the restatement caught |
| MFG-O-SIM-7 | Vendor kernels | On the crash corpus, every crash the declared semantics find is found from the vendor kernel's trace, and every disagreement is reported per block; `SignOff` verdicts rest only on two-host agreement |
| MFG-O-PROG-1 | Regeneration | Unchanged designs keep every `ObjectId`; identical programs diff empty |
| MFG-O-PROG-2 | Templates and setups | Golden programs for template parts; deterministic ranking; each target in one setup |
| MFG-O-PROG-3 | Recognition | Panoptic quality targets on MFInstSeg; training data licensed for commercial use |
| MFG-O-PROG-4 | Agent programs | Held-out agent Proposals pass every oracle; zero bypasses |
| MFG-O-PROG-5 | STEP-NC | Schema validation; round trips exact or within AP242 tolerance |
| MFG-O-PROG-6 | Toolpath edits | Every edit survives a dimension change that keeps its passes and fails typed when a pass disappears; every added lead and link passes the gouge and collision checks; edited toolpaths match a reference re-implementation pass for pass |
| MFG-O-AM-1 | Orientation | Objectives recomputed; brute force on small grids |
| MFG-O-AM-2 | Build hand-off | Named slicers and the bureau's software open the 3MF intact; GP2's mesh export meets its targets |
| MFG-O-AM-3 | Packing | Exact clearance and translational removability |
| MFG-O-AM-4 | Supports and labels | Every overhang and island supported; removal access; labels legible on layers |
| MFG-O-AM-5 | DfAM and lattices | Seeded-defect corpus: every defect found, no clean region flagged |
| MFG-O-AM-6 | Slices | Layer area equals cross-section within the bound; contours closed; bead fill ratio; deposition volume |
| MFG-O-AM-7 | Distortion | Coupon deflection within its uncertainty; AM-Bench 2018 bridge deflection within 10% (target) |
| MFG-O-AM-8 | Compensation | Re-simulated build in tolerance; a compensated metal powder bed build of GP2's geometry within 0.1 mm in phase 2 (target) |
| MFG-O-AM-9 | Cure, sintering, warp | AM-Bench cure depth; measured shrinkage and warp coupons |
| MFG-O-AM-10 | 3MF | Consortium validation and round trip |
| MFG-O-AM-11 | Printer data | bgcode decodes to the same moves with an independent reader; calibration prints reproduce recorded values |
| MFG-O-AM-12 | Strut calibration | Every GP2 strut diameter and angle has at least 18 specimens from three plates; held-out plates fall within the stated uncertainty for diameter, waviness and strength; node corrections fitted on one plate's CT cells predict a held-out plate's cells within the joint envelope |
| MFG-O-MOLD-1 | Mouldability and split | Analytic draft; seeded undercuts; core plus cavity plus part equals the block |
| MFG-O-MOLD-2 | Mould design | Opening collision-free; pin stress, fill imbalance and steel distance in limits; turbulent coolant |
| MFG-O-MOLD-3 | Flow | Centre-gated disk and power-law Hele-Shaw solutions; mass within 0.1%; thresholds calibrated on the step plate and ribbed plaque; warpage bounds cover measured points at the calibrated rate |
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
| MFG-O-PCB-1 | Fabrication packages | Every file the fabricator profile requires; independent readers and a 1 µm XOR against the board empty; ECO's oracles verify the writers |
| MFG-O-PCB-2 | Assembly outputs | Placements from the 3D Assembly within 0.01 mm and 0.1° |
| MFG-O-PCB-3 | Classes and drawing | Each class selects its rule pack; notes equal board values |
| MFG-O-PCB-4 | Panels, stencils, reflow | Panel rules hold; area ratios recomputed; profile inside every part's rating |
| MFG-O-PCB-5 | Rule checks | Seeded-defect boards: every defect found |
| MFG-O-PCB-6 | Test | Coverage recomputed from the netlist; proposed points reach every accessible net |
| MFG-O-HARN-1 | Harness package | Cut list, terminals and test netlist match ELX connectivity; formboard lengths match MEC |
| MFG-O-ASM-1 | Sequences | Every motion replayed collision-free; optimum on small instances; each fastener in one step |
| MFG-O-ASM-2 | Design for assembly | Known minimum part counts; times trace to table rows |
| MFG-O-ASM-3 | Instructions | Every MBOM item consumed; schema and accessibility checks; unchanged designs diff empty |
| MFG-O-ASM-4 | Robots | Replayed paths collision-free; posts reproduce motion; no safety-configuration output; loading paths pass MFG-O-SAFE-3 |
| MFG-O-ASM-5 | Line balancing | All 269 benchmark instances optimal; bounds reported |
| MFG-O-INSP-1 | Characteristics | One characteristic per control and general tolerance; a one-dimension revision changes one balloon and no labels; Form 3 equals the balloons |
| MFG-O-INSP-2 | Plans, methods and CMM | QIF Plans validate and round trip; uncertainty ratios recomputed; paths collision-free on the CMM model |
| MFG-O-INSP-3 | Results | Public QIF samples and CSV templates round trip; one signed record per characteristic, pinned by `CheckId` |
| MFG-O-INSP-4 | Evaluation and scans | Gaussian fits pass ISO 10360-6:2001's error estimation [ISO 10360-6]; known transforms recovered |
| MFG-O-INSP-5 | Uncertainty and decisions | JCGM worked examples reproduced; calibrated artifacts; seeded results at zone edges decided by the guard-band rule |
| MFG-O-QUAL-1 | SPC, MSA, capability | Published chart, capability and gauge R&R examples reproduced exactly |
| MFG-O-QUAL-2 | First articles and nonconformances | Revision C fields complete; seeded changes give the expected partial scope; first-article records join every characteristic and name the revision that ran; use-as-is dispositions exist only as Waivers with serial or lot effectivity |
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
| MFG-O-FAC-8 | Production sites | Two sites with different routings both reconcile against one EBOM revision; costs and ERP mappings differ per site; a seeded unconsumed item fails only at its site |
| MFG-O-SUST-1 | Carbon and inventory | Roll-up equals the sum; mass balance per routing step |
| MFG-O-SUST-2 | Impact | Reference product systems; contributions sum to the total |
| MFG-O-SUST-3 | Circularity | Streams plus losses equal product mass; paths replayed |
| MFG-O-DPP-1 | Passport mapping | Every element mapped or justified as not applicable; carriers decode |
| MFG-O-DPP-2 | Publication | Test-registry round trip; back-up copy at the second provider |
| MFG-O-REG-1 | Restricted substances | Seeded BOMs: every planted case reported with part, material and rule; unknown content never `Pass` |
| MFG-O-REG-2 | 3TG data | Missing due-diligence records reported; no compliance verdict |
| MFG-O-GOLD-1 | Golden products | GP1 and GP2 costs, DfAM verdicts and conformance decisions; GP2 strut calibration; GP3 parts from Crucible programs; GP4 distortion; GP5 warpage and board; GP6 build records and passport |

## Phasing

MFG-O-GOLD-1 collects MFG's gate results. Shared capabilities take their phase from contract 13.4, which the capability tables follow. Press-brake allowance data and metal powder bed compensation keep MFG's phase 2, and toolpath editing, engagement-limited roughing and machine templates meet the parity floor in phase 2.

| Phase | MFG contribution to the gate |
| --- | --- |
| 0 | Core types, `MfgError`, seeded search rules and the protected oracle directory |
| 1 | GP1: coating specification, parametric cost, BOM roll-up and conformance decisions on characteristics; the shop's own CAM. GP2: DfAM and lattice checks, as-built strut and node calibration with B-basis replicates, orientation, 3MF to the bureau, additive cost; no distortion prediction. CAM, posts, simulation, slicing and nesting wait (contract 13.2) |
| 2 | GP3: CAM for housings, shafts and blanks with engagement-limited roughing and toolpath editing; machine packages and templates; gear inspection plans as QIF; four post families with restart points; posted-code simulation and `verify_nc`; the gateway with transfer Acts, bench sessions, registry, offset watch and pull-only DNC; the minimum ceremony and first-article records. GP4: profile cutting, nesting, bend sheets, weld procedures and distortion. One material-extrusion part through Crucible's slicer. Also inherent-strain data, powder bed compensation, in-process drawings and ERP and MES mapping |
| 3 | GP5: mould design, fill, orientation and warpage with its grid-convergence bound; board packages; CMM programs, SPC, MSA and AS9102. Also 5-axis, vendor controller kernels, stability lobes, native bend programs, MTConnect and OPC UA reads, production sites, nonconformance links to corrective actions, passports |
| 4 | GP6: harness package, layup and battery passport. Also gear generating, powder bed scan vectors, joint-scale weld simulation, powder bed thermo-mechanics, PPAP and MES feedback |
| 5 and later | Sheet forming, springback, plating current, bulk forming and GP8's execution class (5); casting simulation and heat-treatment distortion (6) |

## Open questions

1. **Freedom to operate for adaptive clearing.** Does the design-around spiral, with no pre-roughing slot and a single helix or ramp entry, avoid US 9,164,503 and the other engagement-control families, and does trochoidal slotting? Both wait on counsel's opinion, a phase 1 gate item; engagement-limited offset clearing ships in phase 2 either way.
2. **GP2's build-preparation software.** The phase 0 gate fixes the bureau's software and the 3MF extensions it accepts (contract 13.1). Until then GP2 keeps both the Beam Lattice and the mesh 3MF.
3. **Vendor kernel licences.** Will Siemens license Sinumerik's virtual NC kernel to run in a customer-licensed External Op host, and on what terms? The vendor-kernel row waits on that answer; declared semantics serve in the meantime.

## Contract change requests

None.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [3MF Beam Lattice] | 3MF Beam Lattice Extension 1.2.0 | https://raw.githubusercontent.com/3MFConsortium/spec_beamlattice/master/3MF%20Beam%20Lattice%20Extension.md | 2026-10-11 |
| [3MF Core] | 3MF Core Specification 1.4.0, section 3.4 | https://raw.githubusercontent.com/3MFConsortium/spec_core/master/3MF%20Core%20Specification.md | 2026-10-11 |
| [3MF specifications] | 3MF Consortium, specifications | https://3mf.io/spec/ | 2026-10-11 |
| [3MF Toolpath] | 3MF Consortium, Toolpath extension | https://github.com/3MFConsortium/spec_toolpath | 2026-10-11 |
| [AAGNet] | AAGNet, GitHub repository | https://github.com/whjdark/AAGNet | 2026-10-11 |
| [AIAG PPAP] | AIAG, PPAP-4 manual | https://www.aiag.org/training-and-resources/manuals/details/PPAP-4 | 2026-10-11 |
| [AIAG-VDA FMEA] | AIAG and VDA, FMEA Handbook | https://www.aiag.org/training-and-resources/manuals/details/FMEAAV-1 | 2026-10-11 |
| [Altintas et al. 2008] | Altintas, Stepan, Merdol, Dombovari, CIRP J. Manuf. Sci. Technol. 1 | https://www.mm.bme.hu/~stepan/mm/journal2008/altintas_stepan_merdol_dombovari_CIRP.pdf | 2026-10-11 |
| [AOUSD Core 1.0] | Linux Foundation, AOUSD announces OpenUSD Core Specification 1.0 | https://www.linuxfoundation.org/press/alliance-for-openusd-announces-core-specification-1.0-the-universal-language-for-building-3d-worlds | 2026-10-11 |
| [aPriori] | aPriori | https://www.apriori.com/ | 2026-10-11 |
| [async-opcua] | async-opcua, GitHub repository | https://github.com/FreeOpcUa/async-opcua | 2026-10-11 |
| [AutoForm] | AutoForm products | https://www.autoform.com/en/products/ | 2026-10-11 |
| [Bambu Developer Mode] | Bambu Lab, "Updates and third-party integration with Bambu Connect" | https://blog.bambulab.com/updates-and-third-party-integration-with-bambu-connect/ | 2026-10-11 |
| [Bambu Lab 2025] | Bambu Lab, "Firmware update introducing new authorization control system", 16 January 2025 | https://blog.bambulab.com/firmware-update-introducing-new-authorization-control-system-2/ | 2026-10-11 |
| [Bambu Studio CLI] | Bambu Studio wiki, command-line usage | https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage | 2026-10-11 |
| [Bay and Tucker 1992] | "Fiber orientation in simple injection moldings. Part II: Experimental results", Polymer Composites 13(4), 332–341 | https://api.crossref.org/works/10.1002/pc.750130410 | 2026-10-11 |
| [BB&R] | "A Branch, Bound, and Remember Algorithm for the Simple Assembly Line Balancing Problem", doi 10.1287/ijoc.1110.0462 | https://pubsonline.informs.org/doi/10.1287/ijoc.1110.0462 | 2026-10-11 |
| [BIPM JCGM] | BIPM, JCGM publications | https://www.bipm.org/en/committees/jc/jcgm/publications | 2026-10-11 |
| [Boothroyd et al. 2011] | Boothroyd, Dewhurst, Knight, Product Design for Manufacture and Assembly, 3rd ed. | https://www.routledge.com/Product-Design-for-Manufacture-and-Assembly/Boothroyd-Dewhurst-Knight/p/book/9781420089271 | 2026-10-11 |
| [CALYPSO] | ZEISS CALYPSO | https://www.zeiss.com/metrology/en/software/zeiss-calypso.html | 2026-10-11 |
| [Carlson and Beckermann 2009] | Metall. Mater. Trans. A 40 | https://link.springer.com/article/10.1007/s11661-008-9715-y | 2026-10-11 |
| [cavalier_contours] | cavalier_contours, GitHub repository | https://github.com/jbuckmccready/cavalier_contours | 2026-10-11 |
| [Clarabel.rs] | Clarabel.rs, interior-point conic solver (Apache-2.0), GitHub repository | https://github.com/oxfordcontrol/Clarabel.rs | 2026-10-12 |
| [Clipper2] | Clipper2, GitHub repository | https://github.com/AngusJohnson/Clipper2 | 2026-10-11 |
| [CloudNC CAM Assist] | CloudNC, CAM Assist | https://www.cloudnc.com/cam-assist | 2026-10-11 |
| [cppagent] | MTConnect C++ reference agent, Apache-2.0 | https://github.com/mtconnect/cppagent | 2026-10-11 |
| [Cui et al. 2023] | Cui, Rong, Chen, Matusik, ACM TOG 42(4) | https://cdfg.mit.edu/pdf/journal/2023-cui-dense-interlocking-free-and-scalable-spectral-packing-of.pdf | 2026-10-11 |
| [CuraEngine] | CuraEngine, GitHub repository | https://github.com/Ultimaker/CuraEngine | 2026-10-11 |
| [DFMA DFA] | Boothroyd Dewhurst, DFA software | https://www.dfma.com/software/dfa.asp | 2026-10-11 |
| [ECHA Candidate List] | ECHA, Candidate List of substances of very high concern | https://echa.europa.eu/candidate-list-table | 2026-10-11 |
| [ecoinvent] | ecoinvent | https://ecoinvent.org/ | 2026-10-11 |
| [EPA TSCA] | US EPA, summary of the Toxic Substances Control Act | https://www.epa.gov/laws-regulations/summary-toxic-substances-control-act | 2026-10-11 |
| [EU 2015/863] | Commission Delegated Directive (EU) 2015/863 | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32015L0863 | 2026-10-11 |
| [EU Battery Regulation] | Regulation (EU) 2023/1542 | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R1542 | 2026-10-11 |
| [EU conflict minerals] | European Commission, conflict minerals regulation explained | https://policy.trade.ec.europa.eu/development-and-sustainability/conflict-minerals-regulation/regulation-explained_en | 2026-10-11 |
| [EU ESPR] | European Commission, Ecodesign for Sustainable Products Regulation; Regulation (EU) 2024/1781 | https://environment.ec.europa.eu/strategy/circular-economy/ecodesign-sustainable-products-regulation_en and https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202401781 | 2026-10-11 |
| [EU Machinery] | European Commission, Machinery | https://single-market-economy.ec.europa.eu/sectors/mechanical-engineering/machinery_en | 2026-10-11 |
| [EU RoHS] | European Commission, RoHS Directive | https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en | 2026-10-11 |
| [EU WEEE] | European Commission, WEEE Directive | https://environment.ec.europa.eu/topics/waste-and-recycling/waste-electrical-and-electronic-equipment-weee_en | 2026-10-11 |
| [EUR-Lex 2026/1736] | Commission Implementing Decision (EU) 2026/1736 | https://eur-lex.europa.eu/eli/dec_impl/2026/1736/oj | 2026-10-11 |
| [EUR-Lex 2026/1778] | Commission Implementing Regulation (EU) 2026/1778 | https://eur-lex.europa.eu/eli/reg_impl/2026/1778/oj | 2026-10-11 |
| [EVS EN 1090-2] | EN 1090-2:2018+A1:2024 | https://www.evs.ee/en/evs-en-1090-2-2018-a1-2024-consolidated | 2026-10-11 |
| [EVS ISO 10218-1] | ISO 10218-1:2025 | https://www.evs.ee/en/iso-10218-1-2025 | 2026-10-11 |
| [EVS ISO 10218-2] | ISO 10218-2:2025 | https://www.evs.ee/en/iso-10218-2-2025 | 2026-10-11 |
| [EVS welding] | ISO 15609-1:2019, ISO 15614-1:2017 with Amd 1:2019 and ISO 9606-1:2012 | https://www.evs.ee/en/iso-15609-1-2019 and https://www.evs.ee/en/iso-15614-1-2017 and https://www.evs.ee/en/iso-9606-1-2012 | 2026-10-11 |
| [Fanuc CNC] | FANUC America, 5-axis CNC machining and 31i-B5 | https://www.fanucamerica.com/products/cnc/5-axis-cnc-machining and https://www.fanucamerica.com/products/cnc/31i-b5 | 2026-10-11 |
| [FeatureFox] | Fuchs, Kacan, Haag, Lohse, arXiv:2604.26770 | https://arxiv.org/pdf/2604.26770 | 2026-10-11 |
| [Fusion adaptive] | Autodesk Fusion help, 3D Adaptive Clearing | https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/3D-ADAPTIVE-READ.htm | 2026-10-11 |
| [Fusion delete passes] | Autodesk Fusion help, deleting passes or segments | https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/MFG-TOOLPATH-DELETE-OVERVIEW.htm | 2026-10-12 |
| [Fusion Manufacturing Extension] | Autodesk Fusion Manufacturing Extension | https://www.autodesk.com/products/fusion-360/manufacturing-extension | 2026-10-11 |
| [Fusion trim] | Autodesk Fusion help, toolpath trimming | https://help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/MFG-TRIM-OVERVIEW.htm | 2026-10-12 |
| [Gardeyn et al. 2025] | Gardeyn, Vanden Berghe, Wauters, "An open-source heuristic to reboot 2D nesting research", arXiv:2509.13329 | https://arxiv.org/abs/2509.13329 and https://arxiv.org/html/2509.13329 | 2026-10-11 |
| [Goldak et al. 1984] | Goldak, Chakravarti, Bibby, Metall. Trans. B 15, 299–305 | https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/BF02667333 | 2026-10-11 |
| [Haas G-codes] | Haas mill G-codes G00, G234, G268, G187, G81 and G89 | https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G00.html and https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G234.html and https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G268.html and https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G187.html and https://www.haascnc.com/service/codes-settings.type=gcode.machine=mill.value=G81.html | 2026-10-11 |
| [Haas operation] | Haas mill operator's manual, operation and macros | https://www.haascnc.com/service/online-operator-s-manuals/mill-operator-s-manual/mill---operation.html and https://www.haascnc.com/service/online-operator-s-manuals/mill-operator-s-manual/mill---macros.html | 2026-10-11 |
| [Heidenhain TNC] | HEIDENHAIN, PLANE function, Cycle 32 TOLERANCE and TNC 620 cycle programming | https://www.klartext-portal.com/tips/nc-solutions/alignment-with-plane-function and https://www.klartext-portal.com/tips/programming/cycle-32-tolerance and https://content.heidenhain.de/doku/tnc_guide/pdf_files/TNC620/81760x-03/zyklen/1096886-22.pdf | 2026-10-11 |
| [hyperMILL] | OPEN MIND, hyperMILL | https://www.openmind-tech.com/en/ | 2026-10-11 |
| [i_overlay] | i_overlay crate | https://lib.rs/crates/i_overlay | 2026-10-11 |
| [IAQG 9102C] | IAQG, summary of changes in 9102 revision C | https://ma.iaqg.org/wp-content/uploads/2019/10/9102_Changes_07112023.pdf | 2026-10-11 |
| [IEC 62443-3-3] | IEC 62443-3-3:2013 | https://webstore.iec.ch/en/publication/7033 | 2026-10-11 |
| [IPC store] | IPC current revisions (IPC-6012F, IPC-A-600M, IPC-A-610J, J-STD-001J, IPC/WHMA-A-620F, IPC-4761, IPC-D-356B, IPC-1752C) | https://shop.electronics.org | 2026-10-11 |
| [IPC-2581] | IPC-2581 Consortium | https://www.ipc2581.com/ | 2026-10-11 |
| [IPC-2581C] | IPC, IPC-2581 revision C release | https://www.electronics.org/news-release/ipc-releases-ipc-2581-revision-c-generic-requirements-printed-board-assembly-products | 2026-10-11 |
| [ISA-95 Job Control] | OPC 10031-4, ISA-95 Job Control, section 6.3 | https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3 | 2026-10-11 |
| [ISO 10303-238] | ISO 10303-238:2022 | https://www.iso.org/standard/72030.html | 2026-10-11 |
| [ISO 10360-6] | ISO 10360-6:2001 | https://www.iso.org/standard/28095.html | 2026-10-11 |
| [ISO 1328-1] | ISO 1328-1:2013 | https://www.iso.org/standard/45309.html | 2026-10-11 |
| [ISO 13399-1] | ISO 13399-1, cutting tool data representation | https://www.iso.org/standard/36757.html | 2026-10-11 |
| [ISO 14040] | ISO 14040:2006 with Amd 1:2020 | https://www.iso.org/standard/37456.html | 2026-10-11 |
| [ISO 14044] | ISO 14044:2006 | https://www.iso.org/standard/38498.html | 2026-10-11 |
| [ISO 14253-1] | ISO 14253-1:2017 | https://www.iso.org/standard/70137.html | 2026-10-11 |
| [ISO 14649 catalog] | ISO 14649 parts, Accuris store | https://store.accuristech.com/subgroups/29485 | 2026-10-11 |
| [ISO 22093] | ISO 22093:2011 (DMIS) | https://www.iso.org/standard/56444.html | 2026-10-11 |
| [ISO 23952] | ISO 23952:2020 (QIF) | https://www.iso.org/standard/77461.html | 2026-10-11 |
| [ISO 6983-1] | ISO 6983-1:2009 | https://www.iso.org/standard/34608.html | 2026-10-11 |
| [ISO/ASTM 52900] | ISO/ASTM 52900:2021, additive manufacturing terminology | https://www.iso.org/standard/74514.html | 2026-10-11 |
| [jagua-rs] | jagua-rs, collision engine for cutting and packing (MPL-2.0), GitHub repository | https://github.com/JeroenGar/jagua-rs | 2026-10-11 |
| [Janus NX 2606] | Janus Engineering, Siemens NX release 2606 | https://blog.janus-engineering.com/en_en/details/article/siemens-nx-release-2606/ | 2026-10-11 |
| [KiCad 9.0] | KiCad 9.0.0 release notes | https://www.kicad.org/blog/2025/02/Version-9.0.0-Released/ | 2026-10-11 |
| [Kuipers et al. 2020] | Kuipers et al., variable-width extrusion (arXiv:2004.13497) | https://arxiv.org/abs/2004.13497 | 2026-10-11 |
| [LexisNexis DPP] | LexisNexis, Commission launches Digital Product Passport registry | https://www.lexisnexis.co.uk/legal/news/commission-launches-digital-product-passport-registry-under-ecodesign-regulation | 2026-10-11 |
| [Li et al. 2025] | Li, Niu, Sun, Sun, Chinese Journal of Aeronautics 38(2) | https://www.sciopen.com/article/10.1016/j.cja.2024.05.038 | 2026-10-11 |
| [libbgcode] | libbgcode, GitHub repository | https://github.com/prusa3d/libbgcode | 2026-10-11 |
| [Loughborough AMRG] | Loughborough University AMRG, the seven categories of additive manufacturing | https://www.lboro.ac.uk/research/amrg/about/the7categoriesofadditivemanufacturing/ | 2026-10-11 |
| [MAGMASOFT] | MAGMASOFT | https://www.magmasoft.de/en/solutions/magmasoft/ | 2026-10-11 |
| [Manifold] | Manifold, GitHub repository | https://github.com/elalish/manifold | 2026-10-11 |
| [Mastercam] | Mastercam solutions | https://www.mastercam.com/solutions/ | 2026-10-11 |
| [Materialise Magics] | Materialise Magics | https://www.materialise.com/en/industrial/software/magics-data-build-preparation | 2026-10-11 |
| [MDN Web Serial] | MDN, Web Serial API | https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API | 2026-10-11 |
| [Mitsubishi Materials] | Mitsubishi Materials, ToolsUnited article | https://www.mmc-carbide.com/cz/download/magazine/vol10/cut_vol10 | 2026-10-11 |
| [ModuleWorks] | ModuleWorks software components | https://www.moduleworks.com/software-components/ | 2026-10-11 |
| [Moldflow] | Autodesk Moldflow | https://www.autodesk.com/products/moldflow/overview | 2026-10-11 |
| [Moonraker file manager] | Moonraker, file manager API | https://moonraker.readthedocs.io/en/latest/external_api/file_manager/ | 2026-10-11 |
| [MTConnect 2.5] | MTConnect Standard Part 1, 2.5.0 | https://docs.mtconnect.org/MBSD_MTConnect_Part_1_2-5-0.pdf | 2026-10-11 |
| [MTConnect 2.5 Part 3] | MTConnect Part 3, Observation Information Model, 2.5.0 | https://docs.mtconnect.org/MBSD_MTConnect_Part_3_2-5-0.pdf | 2026-10-11 |
| [Murakawa et al. 2010] | Murakawa, Deng, Ma, Trans. JWRI 39(2), 103–105 | https://ir.library.osaka-u.ac.jp/repo/ouka/all/5063/jwri39_02_103.pdf | 2026-10-11 |
| [NeT TG1] | Smith, Smith, Wimpory, Ohms, NeT TG1 single bead on plate, IJPVP 120–121 (2014) | https://publications.jrc.ec.europa.eu/repository/handle/JRC91654 | 2026-10-11 |
| [NIST AM-Bench 2018] | AMB2018-01 bridge structures | https://www.nist.gov/ambench/amb2018-01-description | 2026-10-11 |
| [NIST AM-Bench 2025] | NIST, AM-Bench 2025 measurements and challenge problems | https://www.nist.gov/ambench/am-bench-2025-measurements-and-challenge-problems | 2026-10-11 |
| [NPL MAT 134] | Edser, NPL Report MAT 134, B-basis statistical analysis of FRP composites, February 2026, Table 1 | https://eprintspublications.npl.co.uk/10332/1/MAT134.pdf | 2026-10-12 |
| [nTop] | nTop platform and Yamaha user spotlight | https://www.ntop.com/platform/ and https://www.ntop.com/resources/blog/user-spotlight-yamaha-pairing-topology-optimization-with-graded-lattices/ | 2026-10-11 |
| [NUMISHEET 2014] | Benchmark 2, springback of a draw/re-draw panel, AIP Conf. Proc., doi 10.1063/1.4849980 | https://api.crossref.org/works/10.1063/1.4849980 | 2026-10-11 |
| [NX CAM] | Siemens, NX CAM software | https://www.siemens.com/en-us/products/nx-manufacturing/cam-software/ | 2026-10-11 |
| [NX VNCK] | Siemens, "How NX CAM simulation capabilities validate machines and processes", 2 March 2020 | https://blogs.sw.siemens.com/nx-manufacturing/how-nx-cam-simulation-capabilities-validate-machines-and-processes/ | 2026-10-12 |
| [OctoPrint files API] | OctoPrint, file operations API | https://docs.octoprint.org/en/master/api/files.html | 2026-10-11 |
| [OPC 40001-3] | OPC UA for Machinery, Part 3: Job Management, 1.0.1 | https://reference.opcfoundation.org/Machinery/Jobs/v100/docs/ | 2026-10-11 |
| [OPC 40501-1] | OPC 40501-1, OPC UA for Machine Tools, 1.02.0 | https://reference.opcfoundation.org/MachineTool/v102/docs/ | 2026-10-11 |
| [OPC UA Part 4] | OPC UA Part 4, MessageSecurityMode | https://reference.opcfoundation.org/Core/Part4/v105/docs/7.20 | 2026-10-11 |
| [Open Hub OpenCAMLib] | Open Hub, OpenCAMLib project activity | https://www.openhub.net/p/opencamlib | 2026-10-11 |
| [OpenCAMLib] | OpenCAMLib, GitHub repository | https://github.com/aewallin/opencamlib | 2026-10-11 |
| [openLCA] | openLCA | https://www.openlca.org/ | 2026-10-11 |
| [OrcaSlicer] | OrcaSlicer, GitHub repository | https://github.com/OrcaSlicer/OrcaSlicer | 2026-10-11 |
| [OrcaSlicer 3MF] | OrcaSlicer wiki, publishing 3MF; bbs_3mf.cpp | https://github.com/OrcaSlicer/OrcaSlicer/wiki/publish_3mf and https://github.com/OrcaSlicer/OrcaSlicer/blob/main/src/libslic3r/Format/bbs_3mf.cpp | 2026-10-11 |
| [Ozcan et al. 2024] | Ozcan, Kushwaha, Qian, Reynaerts, euspen ICE 2024 | https://euspen.eu/knowledge-base/ICE24301.pdf | 2026-10-11 |
| [Phelps and Tucker 2009] | J. Non-Newtonian Fluid Mech. 156(3), 165–176, doi 10.1016/j.jnnfm.2008.08.002 | https://api.crossref.org/works/10.1016/j.jnnfm.2008.08.002 | 2026-10-11 |
| [PolyWorks] | PolyWorks Inspector | https://www.polyworks.com/en-us/products/polyworks-inspector | 2026-10-11 |
| [Process Simulate] | Siemens Tecnomatix Process Simulate | https://www.siemens.com/en-us/products/tecnomatix/process-simulate-software/ | 2026-10-11 |
| [PrusaLink OpenAPI] | PrusaLink, OpenAPI specification | https://raw.githubusercontent.com/prusa3d/Prusa-Link-Web/master/spec/openapi.yaml | 2026-10-11 |
| [PrusaSlicer] | PrusaSlicer, GitHub repository | https://github.com/prusa3d/PrusaSlicer | 2026-10-11 |
| [PrusaSlicer 3MF] | Prusa Knowledge Base, saving projects as 3MF | https://help.prusa3d.com/article/saving-projects-as-3mf_1773 | 2026-10-11 |
| [Renoon delegated acts] | Renoon, delegated acts for the Digital Product Passport | https://www.renoon.com/blog/delegated-acts-for-digital-product-passport-explainer-and-current-status | 2026-10-11 |
| [Renoon DPP updates] | Renoon, Digital Product Passport latest updates | https://linguana.renoon.com/blog/digital-product-passport-latest-updates-the-next-developments-to-watch | 2026-10-11 |
| [RoboDK] | RoboDK, offline programming | https://robodk.com/offline-programming | 2026-10-11 |
| [RoboDK Fanuc] | RoboDK documentation, FANUC robots | https://robodk.com/doc/en/Robots-Fanuc.html | 2026-10-11 |
| [RoboDK KUKA] | RoboDK documentation, KUKA robots | https://robodk.com/doc/en/Robots-KUKA.html | 2026-10-11 |
| [RoboDK post processors] | RoboDK documentation, post processors | https://robodk.com/doc/en/Post-Processors.html | 2026-10-11 |
| [RoboDK UR] | RoboDK documentation, Universal Robots | https://robodk.com/doc/en/Robots-Universal-Robots.html | 2026-10-11 |
| [S3-Slicer code] | S3_DeformFDM, GitHub repository (BSD-3-Clause) | https://github.com/zhangty019/S3_DeformFDM | 2026-10-11 |
| [Sandvik Coromant tool data] | Sandvik Coromant, tool data | https://sandvik.coromant.com/en-gb/tools/tool-data | 2026-10-11 |
| [Setien et al. 2019] | Setien et al., "Empirical methodology to determine inherent strains in additive manufacturing", Computers & Mathematics with Applications 78(7) | https://upcommons.upc.edu/handle/2117/132354 | 2026-10-11 |
| [Siemens Lambda Function] | Siemens, partnership with Lambda Function on AI-assisted CNC programming for NX CAM | https://blogs.sw.siemens.com/nx-manufacturing/siemens-partners-with-lambda-function-to-explore-ai-assisted-cnc-programming-for-nx-cam/ | 2026-10-11 |
| [Siemens Sinumerik] | Siemens, SINUMERIK programming manuals | https://cache.industry.siemens.com/dl/files/454/37335454/att_110322/v1/SIN_WF5_0509_en.pdf and https://cache.industry.siemens.com/dl/files/376/24763376/att_80970/v1/PGZ_0108_en_en-US.pdf | 2026-10-11 |
| [SimaPro] | SimaPro | https://simapro.com/ | 2026-10-11 |
| [sparrow] | sparrow, 2D nesting solver (MIT), GitHub repository | https://github.com/JeroenGar/sparrow | 2026-10-11 |
| [STEP Tools AP238e3] | STEP Tools, notes on AP238 edition 3 | https://www.steptools.com/docs/stp_aim/notes_ap238e3.html | 2026-10-11 |
| [SYSWELD] | Keysight, welding simulation (SYSWELD) | https://www.keysight.com/us/en/products/design-engineering-software/computer-aided-engineering-software/welding.html | 2026-10-11 |
| [Tian et al. 2022] | Tian et al., assembly planning by disassembly (arXiv:2211.03977) | https://arxiv.org/abs/2211.03977v1 | 2026-10-11 |
| [Transition Pathways DPP] | EU Transition Pathways, "Digital product passport registry now live" | https://transition-pathways.europa.eu/retail/news/digital-product-passport-registry-now-live | 2026-10-11 |
| [Ucamco Gerber] | Ucamco, the Gerber format | https://www.ucamco.com/en/gerber | 2026-10-11 |
| [Ucamco Gerber downloads] | Ucamco, Gerber format downloads | https://www.ucamco.com/en/gerber/downloads | 2026-10-11 |
| [UR client interfaces] | Universal Robots, overview of client interfaces | https://www.universal-robots.com/articles/ur/interface-communication/overview-of-client-interfaces/ | 2026-10-11 |
| [US 9,164,503] | Google Patents, US 9,164,503 B2 (The Boeing Company) | https://patents.google.com/patent/US9164503 and https://patents.google.com/patent/US9164503B2/en | 2026-10-11 |
| [Valor NPI] | Siemens Valor NPI | https://www.siemens.com/en-us/products/pcb/valor/valor-npi/ | 2026-10-11 |
| [VERICUT] | VERICUT products | https://vericut.com/products | 2026-10-11 |
| [VERICUT Force] | VERICUT Force optimization | https://vericut.com/products/force-optimization | 2026-10-11 |
| [Wang et al. 2008] | Wang, O'Gara, Tucker, J. Rheol. 52(5), 1179–1200, doi 10.1122/1.2946437 | https://api.crossref.org/works/10.1122/1.2946437 | 2026-10-11 |
| [Windchill quality] | PTC, Windchill quality management solutions overview | https://support.ptc.com/help/windchill/plus/r13.0.2.0/pt_BR/Windchill_Help_Center/sublandingpages/wqOvw.html | 2026-10-12 |
| [Zhang et al. 2022] | Zhang et al., S3-Slicer, SIGGRAPH Asia 2022 | https://history.siggraph.org/?p=216073 | 2026-10-11 |
