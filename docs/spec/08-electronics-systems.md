# Electronics and systems (ELX)

Electronics and systems (ELX) is where an engineer designs circuits, printed boards, cable harnesses, motors, batteries, controllers and firmware, and simulates them inside the product they power. Against Altium, KiCad and code-first tools such as JITX, the gain is one versioned design in which board, enclosure, harness and firmware never drift apart and every simulated result carries its error bar. The mechanism: connectivity is typed code, a `Network` of parts joined at typed ports, and the drawn schematic and board layout are data that checks prove equal to it.

## An electronics design, end to end

This section walks one real board through Crucible, so that every later section has a place to attach to. The board is the power stage of GP5, the moulded enclosure with its printed circuit board (PCB) that closes phase 3 (contract section 13.1). It turns a 12 V input into a 3.3 V rail with a buck converter.

### The worked example: GP5's 3.3 V rail

**1. Write the connectivity.** An agent or an engineer writes a feature that returns a `Network`. A `Network` is Crucible's lumped model: elements joined through ports typed by physical domain, compiled by Flux into a set of differential-algebraic equations (a DAE).

```
use std::electronics::{Network, Power, net, port, connect, resistor, capacitor, inductor}
use parts::ti::tps62130                  // definition package pinned in ingot.lock (illustrative)

pub feature buck_3v3(vin: Power, load: Current = 2A) -> Network {
    let n = network {
        let u1   = tps62130()
        let l1   = inductor(1uH ± 20%, i_sat_min: 1.5 * load)          // CatalogSelection
        let c_o  = capacitor(47uF ± 20%, v_rated_min: 10V, dielectric: x7r)
        let r_hi = resistor(100kohm ± 1%)
        let r_lo = resistor(31.6kohm ± 1%)
        let out  = net("3V3")

        connect(vin.pos, u1.pin("PVIN"), u1.pin("AVIN"))
        connect(u1.pin("SW"), l1.a)
        connect(l1.b, out, c_o.a, r_hi.a)
        connect(r_hi.b, r_lo.a, u1.pin("FB"))
        connect(vin.neg, u1.pin("PGND"), c_o.b, r_lo.b)
        let vout = port(Power(out, vin.neg, range: 3.3V ± 2%))
    }
    n.require(dc_voltage(n.vout) in 3.3V ± 2%, name: "vout_regulation")
     .require(ripple_pp(n.vout, load: load) < 20mV, name: "vout_ripple")
}
```

The `network { … }` block is a builder, like `sketch { … }` in mechanical design. Its `connect` statements accumulate into a partition of pins into nets, so their order never matters and repeating one changes nothing. The two `require` lines are checks: named, three-valued predicates that run on every rebuild and gate every merge.

**2. Let the parts resolve.** `inductor(1uH ± 20%, i_sat_min: 1.5 * load)` is a `CatalogSelection`: a request for any approved catalog part that meets the stated limits. Raise `load` to 3 A and the next rebuild picks an inductor with a higher saturation current. Every candidate is read from pinned data, so two engineers on two laptops get the same part.

**3. Draw, or let the drawing be made.** The schematic is a stored drawing of the same connectivity. An engineer can draw a wire, which writes a `connect` into the code, or ask `schematic.autodraw` to propose wires and labels for connections that exist only in code. Either way the blocking check `schematic_matches_network` proves that the drawing and the code describe the same nets.

**4. Put the board in the enclosure.** The bare board is a Part, so its outline and mounting holes are expressions of the enclosure's geometry:

```
let board = pcb(stack, outline: enclosure.face(role: pcb_shelf).inset(0.5mm))
place(j1_usb, at: enclosure.cutout(usb).frame.on(board.top), lock: mech)
board.require(clearance(board.assembled(), enclosure.inner_body()) > 0.5mm, name: "board_clearance")
```

Move the USB cutout 2 mm and the connector follows on the next rebuild; design-rule checking (DRC) then flags any track left too close to it.

**5. Simulate and check.** The ripple check runs Crucible's own circuit simulator on the network. The result is a waveform, which Crucible stores as a `Field<(Ports, Time), Voltage>`. It carries an error budget: one entry per source of error, each either bounded or marked as not quantified (contract section 5.1). Board thermal analysis reads the converter's losses as part power and checks every junction temperature against its derating rule.

**6. Review.** The agent opens a Proposal: a branch, its rationale and its CI report. The reviewer sees a schematic diff of the moved inductor, a per-layer layout diff of the added copper, and the ripple check's verdict on both sides. Merging requires every check to meet the gate, and a merge that would join two nets distinct on both branches stops with `Conflict::NetMerge` instead of shipping a short.

### The model you work with

Six kinds of data make up an electronics design. Geometry stays in Bodies and responses stay in Fields, the two universal types of contract principle 3.

| Concept | What it is | How it relates to the core types |
| --- | --- | --- |
| `Network`, `Net`, `Pin`, `Port` | Connectivity: Instances of catalog parts, nets, and typed ports; compound ports such as `Power`, `I2c`, `Spi`, `UsbC` and `Can` group roles | `Network` is a core type; ports are records marked `#[interface]` |
| `Schematic` | The drawn topology of one `Network`: symbols, segments, junctions, labels, sheets | A data module of table rows, checked against connectivity |
| Catalog part | A purchasable part's pins, footprints, models and offers | A Package under `parts::<manufacturer>::…`; offers are External inputs |
| `Stackup`, `Layout` | The board's layers and its placements, tracks, vias and zones | Plain values and integer-coordinate data modules |
| Bare and assembled board | The printed board, and the board with its parts | A Part of kind `pcb`, and an Assembly |
| Results | Waveforms, spectra, sweeps, temperatures, S-parameters | Fields such as `Field<(Ports, Frequency), Complex<Impedance>>` |

**Decision D-ELX-1:** Connectivity is Ingot code, and a schematic is a stored drawing that the blocking check `schematic_matches_network` proves equal to it.
*Why:* agents and the code editor need text connectivity, which merges semantically and type-checks before it runs, and atopile shows that code capture works in practice [atopile].
*Rejected:* the drawing as the source, as in KiCad and Altium, whose geometric connectivity merges badly; drawings generated from code, which lose the signal-flow layout engineers read; an unchecked drawing beside the code.

**Decision D-ELX-2:** Every catalog part used in a network is an Instance of the Part its definition package describes; the bare board is a Part, and the assembled board an Assembly.
*Why:* one derived BOM view covers mechanical and electrical items, and moving a part in layout is the same edit as moving it in the assembly.
*Rejected:* a separate symbol-instance concept, which duplicates Instance and needs a synchronization step.

[[DIAGRAM diagrams/08-electronics-source-model.jsx: electrical source model · what editors write and what Kiln derives]]

Read it left to right: outlined boxes are files that editors and agents write, tinted boxes are what Kiln derives, and the dashed arrow is enclosure geometry driving the board.

### Why this beats the code-first newcomers

Code capture alone is no longer rare. JITX lets AI write Python design code and generates pin assignments and routing [JITX]. The tscircuit project is an MIT-licensed "React for Electronics" with a registry and autorouting [tscircuit]. The browser tool flux.ai calls itself "your AI hardware engineer", with live parts data and collaboration built in [flux.ai]. Code capture itself is quick to copy; what follows is not, because it rests on the rest of Crucible.

1. **One repository for the whole product.** Enclosure, board, harness and firmware share one Kiln graph, so the USB cutout and the connector cannot disagree. ELX-O-BRD-2 proves it on scripted enclosure changes.
2. **Checks with error budgets and validity envelopes.** A simulated ripple carries its algebraic, temporal and input errors, and an out-of-range model says so. ELX-O-SIM-1 verifies the budget.
3. **Exact, deterministic DRC.** Copper is integer data with exact predicates, so every platform reaches the same verdict. ELX-O-LAY-1 checks against an exact rational reference.
4. **Semantic merges.** Two branches that join different nets at one pin fail with `Conflict::NetMerge` instead of merging into a silent short. ELX-O-NET-2 seeds such pairs.
5. **Approvals over digests and verified agent work.** Every agent Proposal is attacked by an independent verifier, and flashing a board needs a human Approval of the exact image. ELX-O-SYS-3 and ELX-O-FW-3 verify the binding.

The measured target, at phase 3: an agent takes GP5's board from requirements to a DRC-clean Proposal with fewer human corrections than a recorded JITX or flux.ai session needs.

### What ELX owns

ELX owns connectivity, the `network { … }` builder and its element libraries, catalog parts' electrical facets, schematic capture, the board model, layout and DRC. It also owns electrical, mechatronic, battery, power, fluid-system and control models, harness connectivity, robot export and requirements traceability, in `std::electronics` and `std::systems`. Neighbouring tabs own the rest:

| Concern | Owner | What ELX contributes |
| --- | --- | --- |
| Network compilation, the DAE solver, sparse LU, field solvers, RLCG extraction, plant linearization, the FMI runtime | FLX | Port types, element libraries, the Verilog-A front end, vector fitting of extracted data |
| Fabrication and assembly packages, panels, stencils, rule packs, test programs, the harness package | MFG | The board model; the DRC engine that runs MFG's rule packs |
| Harness 3D routing and formboard geometry; declared mass properties | MEC | Harness connectivity, wire tables, electrical checks; catalog mass facets |
| Catalog service, the registry, every `io/` reader and writer, ECAD migration, the Modelica reader | ECO | The electrical meaning of each format; element libraries the reader targets |
| Schematic, layout and constraint canvases; the Electronics preset; Proposal review | UIX | Content drawn through `crucible:ui/canvas2d`; schematic and layout diff nodes |
| Merge driver, variant semantics, the 150% BOM, Items, the obsolescence check | KLN | Net partitions; `bare_board_invariant`; the variant covering-set policy |
| Act machinery, `edit.stream` and the approval page | AGT | `flash_device` and bench-session plan contents and board hazards |
| Materials, physics models, validity envelopes, the parity map | COV | Cell, machine and dielectric models; the board workflow tiers |

Out of scope, stated plainly:

- Integrated-circuit and FPGA internals; chips enter only as catalog-part models.
- Regulatory verdicts; EMC, safety and radio results are screening evidence for a test lab.
- Real-time execution; hardware-in-the-loop runs outside Kiln.
- Device physics below compact models, arcs in contactors and fuses, and electrochemistry below porous-electrode theory.
- Field-life forecasts; handbooks give comparative failure rates.

Before the phase 1 gate, electronics work is a circuit-simulation research track (contract section 13.2), so every ELX capability lands in phase 2 or later. New electrical physics enters only through the public mechanisms anyone can use (principle 1). An acoustic domain, for example, is a package declaring one port type.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| New lumped domain | Package with a port type: across, through and power expression | Power expression is not a power: compile error | ELX-O-EXT-1 | 2 |
| New device model | Verilog-A or Ingot equation element with envelope and oracle cases | Unsupported Verilog-A construct listed with file and line | ELX-O-SIM-3 | 3 |
| New analysis | Ingot feature, or Wasm component calling `crucible:ops/flux`, returning Fields and checks | Determinizer rejection with the offending instruction | ELX-O-EXT-1 | 3 |
| New exchange format | `io/` Wasm component with a round-trip oracle | Unmapped items listed, never dropped | ELX-O-SCH-3 | 3 |

## Networks

A design needs one way to say what connects to what, in every physical domain, that merges safely and type-checks before anything runs. This section defines that model; later sections only add element libraries to it.

### One lumped model for every domain

**Decision D-ELX-15:** `Network`, built with `network { … }`, is the lumped model for every physical domain, compiled by Flux into one DAE.
*Why:* one mechanism serves where separate circuit, block-diagram and physical-network tools would each need their own editor and adapters, so a motor drive from inverter to propeller is one model.
*Rejected:* separate formalisms per domain, which need adapters at every boundary; a circuit-only type, which leaves thermal, mechanical and fluid parts outside.

Electrical, magnetic, thermal, rotational, translational, fluid and signal ports join through the same `connect`. Each port type declares its across quantity (voltage, temperature, angular velocity), its through quantity (current, heat flow, torque) and its power expression, which the compiler checks is a power. Across quantities are equal at a node, through quantities sum to zero, and signal ports are causal.

Flux compiles and integrates Networks ([FLX, Networks](03-flux.md#networks)). ELX supplies the element libraries, including drivetrain elements built from MEC's gear records. Each element states its validity envelope; lumped wiring, for example, holds while a line is shorter than a tenth of a wavelength. FLX also owns the compile-time target: an edit to one element of a 50,000-equation Network recompiles only the changed part.

### Hierarchy, buses and ports

- **Hierarchy.** A sub-network is a feature returning a `Network`, and repeated channels are loops keyed per contract section 5.5. It adds an Assembly level only when the designer declares a sub-assembly, such as a daughterboard.
- **Buses.** A bus is a compound `#[interface]` port or a net vector (`Bus<8>`). Joining compound ports checks roles, and an incompatible join is a compile error that suggests an adapter part.
- **Global nets.** None are implicit; a design may declare `global_net("GND")` once at the top level.
- **Electrical typing.** `Power` carries a `Tol<Voltage>` range, and pins carry absolute-maximum ranges. Static mismatches fail at compile time; value-dependent ones become checks.

### Net ties and merges

**Decision D-ELX-21:** Two named nets join only through an explicit `tie(net_a, net_b, at: footprint)`, which rule checks, netlists and IPC-2581 export treat as one intended short.
*Why:* union semantics would turn two branches attaching one pin to different nets into a silent short, yet star grounds and current-sense points need visible, intended shorts.
*Rejected:* letting union semantics join named nets; net ties as drawing-only symbols, which netlists and DRC cannot see.

A pin that `connect` places in two named nets fails the unwaivable rule `named_net_join`, naming the pin, both nets and both statements. Nets match by the `CallSite` of their `net(…)` call, never by name.

Kiln derives each design's net partition as a node. A merge that unions nets distinct in the base and in each side is `Conflict::NetMerge`, naming the pins, nets and Changes; this is the connectivity merge condition of contract section 7.1. It also covers harness Networks and `std::systems` interface connections.

### Several boards, one system

**Decision D-ELX-33:** A product with several boards is one Network and one Assembly, and `mate(connector_a, connector_b)` joins directly mated connectors, with pin correspondence from mating facets and placement.
*Why:* a mezzanine pinout mirrored across the mating plane is the commonest multi-board error, and deriving the correspondence from geometry catches it without any system-level synchronization step.
*Rejected:* a separate system schematic of board modules kept in step with each board, as Altium's multi-board projects do [Altium multi-board]; hand-written pin maps between boards.

The rule `mated_pinout` fails on a pair whose pins are mirrored or whose roles are incompatible, such as an output facing an output. A cable between boards is a harness Network, and the same net partition and merge condition cover it.

### Variants

**Decision D-ELX-4:** A board's variants are `#[configuration]` record parameters under KLN's option semantics, and CI builds the listed sellable configurations plus a pairwise covering set.
*Why:* variants reuse Kiln's caching and checks, and region, feature and assembly options follow one model across mechanical and electrical design.
*Rejected:* one variant enum built exhaustively in CI, exponential in the options; variant tables beside the design, a second mechanism with its own merge rules.

Fitted state, part choice and values are `if` and `match` expressions on the options. KLN owns variant semantics, the symbolic 150% BOM and its oracle ([KLN, Effectivity and variants](05-kiln-repo-plm.md#effectivity-and-variants)); ELX owns the covering-set policy and the bare-board rule below.

```
#[configuration]
pub struct Options { region: Region, lite: bool }

let r_term = resistor(120ohm ± 1%).fitted(!opts.lite)        // land pattern stays on the bare board
let modem  = match opts.region {
    Region.eu => modem_eu,                                   // both CatalogSelections require
    _         => modem_na,                                   // land_pattern: lga_52
}
```

An unfitted part keeps its land pattern and leaves the assembly BOM and placement data. The check `bare_board_invariant` reuses the 150% BOM's abstract interpretation. Every branch reaching copper, drill, outline, mask or silkscreen must give one `GeometryId`, or the check fails naming the configuration and item. Copper that truly differs needs a declared fabrication variant with its own bare-board Item, and each variant states paste handling for unfitted parts.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Network builder | `network { … }` returns a `Network`; `connect` is order-independent and idempotent. Requires: FLX `flux::compile_network` | Type errors at compile time with fixes, such as an adapter part | ELX-O-NET-1 | 2 |
| Domain port types | Across, through and power expression; std ports for every domain above | Power expression not a power: compile error | ELX-O-NET-3 | 2 |
| Drivetrain elements | Gear ratio, mesh stiffness, couplings and bearing friction with rotational ports, parameterized from MEC's gear records | A gear record missing a parameter is a typed error naming it | ELX-O-NET-3 | 2 |
| Electrical element library | Modified-nodal-analysis stamps for passive, source, switch and controlled elements, each with an envelope | Element outside its envelope flagged with the variable | ELX-O-NET-3 | 3 |
| Hierarchy and buses | Sub-networks as features; `#[interface]` ports with roles; `Bus<N>` | Role or port mismatch is a compile error | ELX-O-NET-1 | 3 |
| Net ties | `tie(net_a, net_b, at:)`; rule `named_net_join` | Unwaivable error naming the pin, nets and statements | ELX-O-NET-2 | 3 |
| Net partition for merges | Derived partition, nets matched by provenance | `Conflict::NetMerge` with pins, nets and Changes | ELX-O-NET-2 | 3 |
| Mated board-to-board connectors | `mate(connector_a, connector_b)` from mating facets and placement; rule `mated_pinout` | Mirrored or role-incompatible pair fails naming both pins | ELX-O-NET-2 | 3 |
| Variant covering set | `#[configuration]` records under KLN's semantics; CI builds sellable configurations plus a pairwise covering set. Requires: KLN Variants and 150% BOM | An unbuildable configuration fails CI and is named | ELX-O-VAR-1 | 3 |
| Bare-board invariance | `bare_board_invariant` over every branch | Fails naming the configuration and the differing item | ELX-O-VAR-1 | 3 |

## Schematic capture and review

Engineers read circuits as drawings, and reviewers judge electrical changes visually, so Crucible keeps a real schematic beside the code and shows every change in electrical terms. This section defines the stored drawing, how editors and agents keep it equal to the `Network`, the electrical rule checks, and the diff views a reviewer sees.

### The drawn schematic

The `Schematic` module stores drawn topology as table rows with stable ids, one row per item. Segment ends lie on pins, labels, power symbols, sheet pins or other segments at explicit junctions. No-connect flags and bus entries are rows too.

```
// buck_3v3.schematic.ingot, written by the schematic editor
pub const drawing = schematic(of: buck_3v3, frame: a4,
    symbols: table {
        id | at           | rot
        u1 | (60mm, 40mm) | 0deg
        l1 | (90mm, 40mm) | 0deg
    },
    segments: table {
        id  | from         | to                               | via
        s_7 | u1.pin("SW") | l1.a                             | [(78mm, 40mm)]
        s_8 | l1.b         | junction(j_2, at: (100mm, 40mm)) | []
    },
    labels: table {
        text  | at            | on
        "3V3" | (110mm, 40mm) | s_8
    },
)
```

**Decision D-ELX-27:** `Schematic` and `Layout` stay Ingot text with no binary sidecar: each is a module of `table { … }` literals whose rows are atomic merge blocks.
*Why:* a second storage format would bypass block-level merge, live documents, span provenance, text-derived `CallSite`s and Git export.
*Rejected:* a binary sidecar keyed by statement identity, even as a fallback for very large boards; one module per board whatever its size.

ING's row lexer parses rows without the general syntax tree and builds lossless nodes lazily on edit. The target is 10⁶ rows, about a 20-layer, 10,000-net board (an estimate), parsed and hashed in under 1 s natively. Above it, the layout splits into modules by board region, which merges and live documents already handle.

Because rows merge one by one, several designers can work on one board at once. Two designers routing different regions of one board work on branches or live in one document, merge row by row, and see a `Conflict::NetMerge` instead of a silent short. Browser tools such as flux.ai build real-time collaboration in [flux.ai]; Crucible adds merges that detect connectivity conflicts, for every user.

Editor behaviour follows from the connectivity decision:

1. Drawing a segment writes a `connect` into the network block that owns both pins; crossing a hierarchy boundary adds a port. No-connect flags and net-tie symbols write `no_connect` and `tie`. Placing a label with an existing net's name writes a `connect`, and editing a label renames the net.
2. A connection made only in code renders dashed until it is drawn. `schematic.autodraw(nets)` proposes the drawing for such connections, as described below.
3. `schematic_matches_network` blocks release. A drawn group spanning two nets is `SchematicError::DrawnShort`, shown in the danger style; an item on a removed pin is `SchematicError::StaleAnnotation` with a one-click fix.
4. Moving a symbol edits one row of the `Schematic` module, so branches moving different symbols merge cleanly.
5. Connectivity generated by a loop is read-only in the drawing; editing it opens the generating line.

Off-page connections are labels with generated cross-references. Reference designators live in the module, change only by an explicit renumber shown as a diff, and never influence geometry (contract section 7.1). The editors run on UIX's canvases in the Electronics preset ([UIX, Electronics](10-ui.md#electronics)).

### Drawing what the code connected

Agents and the code editor change connectivity in text, so without help every such edit would leave manual drawing work before release.

**Decision D-ELX-37:** `schematic.autodraw(nets)` is a deterministic Wasm component that proposes segment or label rows for connections made only in code, and its output is a Proposal a person reviews.
*Why:* agents cannot draw by gesture, yet the drawing must match the network before release, so a reviewable proposal keeps both agent speed and human-readable schematics.
*Rejected:* generating the whole drawing from code on every rebuild, which discards signal-flow layout; leaving code-only connections for a person to draw.

The component routes short connections as wires and uses net labels when a wire would cross more than a stated number of symbols (default 3). It orders its work by canonical numbers, never by names, so the same inputs give the same rows.

### Electrical rule checks

Electrical rule checks (ERC) live in `std::electronics::erc` and re-run only for the nets an edit touched. Each has a severity, an explanation and a fix. `#[waive(…)]` in source only requests a Waiver; the rule keeps failing until an authorized person signs a matching Waiver record (contract section 5.4). A Waiver whose rule no longer fires raises a warning. The rule families are listed under [Reference](#erc-rule-families).

### Review in electrical terms

A row diff of segment coordinates says nothing to an electrical reviewer, and a geometric diff of copper shows where things changed but not what changed electrically.

**Decision D-ELX-32:** Proposal review of electronics shows three derived views, each a Kiln node: a schematic diff, a layout diff and a net-partition diff.
*Why:* incumbent electronics review is visual and net-aware, and computing the views from the net partition and the integer layout data makes them exact and cacheable.
*Rejected:* row diffs of the data modules, which are unreadable; screenshots of both versions, which hide connectivity changes; geometric diffs alone, which miss a pin moved to another net.

- **Schematic diff.** Symbols added, removed or moved; wires whose net membership changed, highlighted in both versions; value and part changes.
- **Layout diff.** A per-layer copper XOR computed exactly from the integer data, moved parts with displacement arrows, and changed rules with the objects they now affect.
- **Net-partition diff.** Nets merged, split and renamed, with the pins that moved between them.

UIX shows these views in Proposal review for the Electronics preset, beside the check verdicts of both sides.

### Netlists and import

Netlists export as SPICE, KiCad netlist and EDIF 2 0 0, the ANSI/EIA-548 version whose netlist view tools still support [Wikipedia EDIF]. KiCad schematics import through an `io/` Wasm component: wires become `connect` statements, the drawing becomes the `Schematic` module, and near-miss wires are listed. Designs from other tools arrive through ECO's migration path ([ECO, Migration](11-interop-ecosystem.md#migration-from-incumbent-tools)), which ends in the same importer. Teams that keep some boards in KiCad during a migration can use KiCad's IPC API, Protocol Buffers over NNG, as a live bridge [KiCad IPC API].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Drawn topology | Segments, junctions, labels, power symbols, sheet pins, no-connect flags, bus entries as table rows | `SchematicError::StaleAnnotation` with a fix | ELX-O-SCH-1 | 3 |
| Drawing matches network | `schematic_matches_network`, blocking | `SchematicError::DrawnShort` fails release | ELX-O-SCH-1 | 3 |
| Automatic drawing | `schematic.autodraw(nets)` proposes rows for code-only connections as a Proposal | A net it cannot draw within the crossing limit is labelled instead and listed | ELX-O-SCH-1 | 3 |
| Labels as connectivity | Label edit renames the net; an existing name writes a `connect` | Rename onto another net's name is a typed error naming both | ELX-O-SCH-1 | 3 |
| Reference designators | Stored and stable; explicit renumber as a diff | Duplicate designator is a `Failure` naming both Instances | ELX-O-SCH-1 | 3 |
| Pin and gate swap | Within catalog swap groups, from schematic or layout, as one source edit | Swap outside a group refused with the group | ELX-O-SCH-1 | 3 |
| ERC | Checks over the `Network` and catalog data, incremental by net; Waivers per contract section 5.4 | Violation with rule, location and fix; stale-Waiver warning | ELX-O-SCH-2 | 3 |
| Electronics review diffs | Schematic, layout and net-partition diffs as Kiln nodes, shown in Proposal review | A diff over a module that failed to parse is `Failed` naming the module | ELX-O-SCH-6 | 3 |
| Netlist export | SPICE, KiCad, EDIF 2 0 0 | Unsupported construct listed, never dropped | ELX-O-SCH-3 | 3 |
| Schematic import | KiCad directly; other tools through ECO's migration path. Requires: ECO ECAD migration | Near-miss wires and unmapped objects listed | ELX-O-SCH-3 | 3 |
| Design blocks | Sub-network plus layout fragment published as a package | A fragment that cannot place is reported; the schematic still applies | ELX-O-SCH-3 | 4 |
| Drawing output | PDF with title blocks and cross-references; lifecycle text late-bound | None: output is rendered from data already checked by `schematic_matches_network` | ELX-O-SCH-4 | 3 |
| Data modules at scale | `Schematic` and `Layout` as `table { … }` rows; region split above the parse target | A module over the target is reported with its parse time and a split Proposal | ELX-O-SCH-5 | 3 |

## Catalog parts

A board is mostly bought parts, so every pin, footprint, model and price has to be trustworthy, pinned and reviewable. This section defines a catalog part's electrical facets, how a design picks parts, and how parts are created and migrated.

### Electrical facets

A catalog part's definition is a signed data Package under `parts::<manufacturer>::…`, pinned in `ingot.lock`, and its offers are External inputs (contract section 2). MEC owns its mechanical facets.

| Facet | Contents | Typed as |
| --- | --- | --- |
| Identity | Manufacturer, part number, lifecycle, package, compliance | Plain values |
| Pins | Name, electrical type, alternate functions, swap groups, ranges | `Pin` records with `Tol<Voltage>` |
| Symbols and footprints | Symbol units; land patterns with pad-to-pin map and courtyard | Data modules; `Footprint` |
| 3D body | Exact body from ECO's STEP reader, envelope Body, keep-out Body | `Body` in CAS |
| Mass properties | Declared mass, centre of gravity and optional inertia, with source `Datasheet` or `Measured` | `Tol<Mass>`, `Tol<Point>` |
| Mating | Mating connector families and pin correspondence | Plain values |
| Specifications | Capacitance, ratings, saturation current, θJA, with test conditions | `Quantity<D>` and `Tol<T>` |
| Models | SPICE, Verilog-A, IBIS, IBIS-AMI, Touchstone, thermal, magnetics | References, each with a `ValidityEnvelope` |
| Reliability and rules | Failure-rate category, derating curves, datasheet layout rules | Plain values and checks |
| Offers | Price breaks, stock, lead time | External inputs |

The mass facet exists because purchased parts arrive as simplified or hollow STEP bodies, so their computed mass can be wrong by large factors. MEC's declared mass properties use it in place of the computed values. A warning flags a purchased Instance whose computed mass is used without a declaration ([MEC, Standard parts and fasteners](06-mechanical.md#standard-parts-and-fasteners)).

**Decision D-ELX-5:** Supplier offers enter evaluation only as signed, pinned External inputs changed by an explicit update, and BOM views date every offer.
*Why:* stock changes hourly and principle 4 forbids reading live data during evaluation, while cost checks still need prices.
*Rejected:* live supplier lookups during evaluation; offers wholly outside evaluation, which hides cost from checks.

### Choosing parts

**Decision D-ELX-3:** A network element names an exact catalog part, an internal part number or a `CatalogSelection`, which re-resolves until the layout's first release.
*Why:* designers state intent (`1uH ± 20%`), and a load change should re-pick the inductor, but a released part choice changes only by change order.
*Rejected:* resolving only at lockfile updates, which leaves picks stale; re-resolving after release, which swaps placed parts silently; calling a selection a `Query`; exact-only selection.

A selection is a pure function over pinned definitions, plus pinned offers when it ranks by price or stock. `crucible update parts` refreshes only the data pins and lists every substitution. A selection matching nothing fails with `SelectionError::NoCatalogMatch`, naming the tightest constraint and the nearest candidates, and never widens its constraints.

When a board's layout is first released or locked, each selection records its part in the BOM data module as `resolved: parts::…`. Re-resolution then opens a Proposal with its reason ("selection now prefers X") instead of changing the part. A re-pick that changes the land pattern fails with `SelectionChangesLandPattern`, and ranked picks never change a released assembly BOM outside a change order.

**Decision D-ELX-22:** An organization's parts-policy package lists approved internal part numbers with approved manufacturers, lifecycle and preferred flags; a `CatalogSelection` resolves over approved parts first and reaches the open catalog only under a Waiver.
*Why:* companies design with internal numbers their parts engineers control, so open-catalog picks alone make the design, the ERP system and the assembly BOM disagree.
*Rejected:* manufacturer part numbers only; an approved-parts database outside the repository.

BOM views list each internal number with its approved manufacturers. A new-part request is one Proposal creating the internal number, its facets and its approved manufacturers, and MEC's fastener selection reads the same policy.

Parts go end-of-life, and that is the main reason released BOMs change. ECO's catalog connector turns a manufacturer's lifecycle change or product change notice into a dated External input update on a monitoring branch, never on released source. KLN's nightly obsolescence check then reports each affected end item ([KLN, BOM views and where-used](05-kiln-repo-plm.md#bom-views-and-where-used)). The report lists the Items and effectivity, alternates found by re-running each `CatalogSelection` without the part, and a last-time-buy quantity when ERP demand is available. ELX's part is that every selection can re-run with exclusions and report its candidates.

### Footprints and symbols

Land patterns follow IPC-7351B by default, whose 2010 edition defines three density levels per package [IPC-7351B release]. IPC lists IPC-7351B and the IPC-7352 guideline side by side among its current design standards [IPC design standards]. Each generator reads its standard from a pinned package naming the document and edition, so moving to IPC-7352 is an explicit update.

Footprint generators (`std::electronics::footprint::qfn`, `soic`, `bga`, `chip`, `sot`) compute toe, heel and side fillets from toleranced package dimensions. KiCad generates over 78% of its footprints from data [KiCad 10 release]; Crucible's target is 100% for standard packages.

```
let fp = footprint::qfn(
    body: (4mm ± 0.1mm, 4mm ± 0.1mm), pitch: 0.5mm, pins: 24,
    lead_len: 0.4mm ± 0.05mm, exposed_pad: (2.6mm, 2.6mm),
    density: Density.nominal, standard: land_patterns::ipc_7351b,
)
.require(paste_coverage(fp.exposed_pad) in 50% .. 80%, name: "ep_paste")
```

Symbols are generated from the pin table, which is the source, as KiCad 10's CSV pin tables suggest [KiCad 10 release]; a librarian may refine the view. Alternate body styles follow the IEC 60617 database [IEC 60617] or IEEE 315-1975, which IEEE has listed as inactive-reserved since 2019 [IEEE 315].

### Creating and migrating catalog parts

1. **From a datasheet.** An agent extracts values into a record Proposal, citing page and table for each. AGT's quarantined extraction reads the datasheet, so the values are `data_untrusted` and the agent's context stays clean ([AGT, Quarantined extraction](09-agents.md#quarantined-extraction-and-external-hosts)); a person approves.
2. **From libraries.** KiCad libraries import into organization-private packages, or into public packages licensed CC-BY-SA-4.0 with attribution kept, because KiCad's licence binds redistributed collections [KiCad library licence]. EAGLE XML arrives through ECO's importer. Altium, CADSTAR, EasyEDA, P-CAD, Fabmaster, Allegro and PADS files arrive through KiCad 10's importers in a pinned container. KiCad 10 reads Allegro boards from versions 16 to 23, and PADS schematics and boards [KiCad 10 importers].
3. **By hand.** The symbol and footprint editors write the same data modules.

Operator-curated `parts::` packages hold only cited facts and geometry from Crucible's own generators ([ECO, Mirrors, licences and the parts catalog](11-interop-ecosystem.md#mirrors-licences-and-the-parts-catalog)). Manufacturer CAD files enter only where their terms allow redistribution.

Every record is checked before publication: pins equal pads, the courtyard encloses the body, and pin types and SPICE port order match the IBIS pin list and pin map. A failure blocks publication with a `CatalogError` naming the facet.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Electrical facets | Versioned record of the facets above, mass and mating included | A missing facet blocks only the uses that need it | ELX-O-CAT-1 | 3 |
| Consistency checks | Pins, pads, symbol, models and body agree | `CatalogError` blocks publication | ELX-O-CAT-1 | 3 |
| `CatalogSelection` | Pure over pinned definitions and offers; re-resolves when arguments change; recorded as `resolved:` once the layout is released; re-runs with exclusions for alternates | `SelectionError::NoCatalogMatch` with nearest candidates; `SelectionChangesLandPattern` | ELX-O-CAT-3 | 2 (selection over pinned definitions), 3 (offers, land patterns, layout release, exclusions) |
| Offers | External inputs pinned in `ingot.lock`, dated in BOM views | An offer past its validity period is labelled with its age | ELX-O-CAT-3 | 3 |
| Parts policy | Approved internal numbers first; open catalog only under a Waiver | KLN's parts-policy check fails unless a Waiver names the part | ELX-O-CAT-4 | 3 |
| New-part requests | One Proposal creates the internal number, facets and approved manufacturers | Missing facets listed in review | ELX-O-CAT-4 | 3 |
| Footprint generators | Toleranced package dimensions to `Footprint` under a pinned land-pattern package | Dimensions outside a family are a typed error; `CatalogError::PinPadMismatch` | ELX-O-CAT-2 | 3 |
| Symbol generation | Pin table to symbol view | Unplaced pin listed; `CatalogError::SymbolPinMismatch` | ELX-O-CAT-1 | 3 |
| Datasheet extraction | PDF to a record Proposal with page references. Requires: AGT Quarantined extraction | Values without a source reference are rejected | ELX-O-CAT-5 | 4 |
| Library migration | KiCad, EAGLE and other libraries to catalog parts in private or CC-BY-SA-4.0 packages | Unmapped fields listed; the registry refuses a package without a redistributable data licence | ELX-O-SCH-3 | 3 |

## The board as a Part

The board has to be a real mechanical object as well as a carrier of copper, so that the enclosure, the fabricator and the analyses all read one model. This section defines the stackup, the integer layout geometry, the Bodies derived from it, and the board's place in the product.

### Stackup

A `Stackup` is an ordered list of layers plus the via spans a fabricator can build. Dielectric permittivity and loss are Fields over frequency, fitted with a causal multi-pole Debye model. Laminate records carry IPC-4101 slash-sheet designations [IPC standards list], and copper layers carry weight, `Tol<Length>` thickness, roughness and a role.

```
let stack = stackup(name: "6L-1.6mm", layers: [
    copper(L1, 35um, role: signal),     prepreg(fab::it180a_2116, 0.11mm ± 10%),
    copper(L2, 35um, role: plane(GND)), core(fab::it180a_core, 0.71mm ± 10%),
    copper(L3, 35um, role: signal),     prepreg(fab::it180a_7628, 0.2mm ± 10%),
    copper(L4, 35um, role: signal),     core(fab::it180a_core, 0.2mm ± 10%),
    copper(L5, 35um, role: plane(PWR)), prepreg(fab::it180a_2116, 0.11mm ± 10%),
    copper(L6, 35um, role: signal),
], vias: [through(L1, L6), blind(L1, L2, laser), buried(L3, L4)])
.require(total_thickness(stack) in 1.6mm ± 10%, name: "stack_thickness")
```

Materials and spans come from MFG's capability records (`fab::…`), so changing fabricator re-checks the board; an unbuildable span fails with `StackupError::UnsupportedSpan`. A board may hold one stackup per outline region (rigid, flex, cavity, stiffener).

**Decision D-ELX-23:** A board declares `fab_class` and `assembly_class` (Class 1, 2, 3 or 3/A), selecting MFG rule packs pinned in licensed data packages.
*Why:* the class changes annular ring, plating and acceptability rules, so checks must read it, and Class 1 governs much consumer work.
*Rejected:* one rule set for every class; the class as a drawing note only.

The current editions are IPC-6012F, IPC-A-610J and IPC J-STD-001J [IPC standards list]. IPC released the last two on 8 April 2024 [IPC J revisions]. MFG's fabrication-drawing generator writes the board's class, materials, finish and impedance tolerances with the acceptance notes.

### Board geometry

**Decision D-ELX-6:** Authored layout geometry is integer data in nanometres per board, bounded to ±2^40 nm, with exact predicates through `anvil-planar`.
*Why:* integer data makes DRC and fills identical everywhere at tens of bytes per track, and Crucible's fills pass its own exact DRC.
*Rejected:* copper as B-rep Bodies, too heavy for routing; floating-point coordinates; rounding to nearest; three-point arcs, whose offsets leave the grid.

Tracks, pads, vias and zone outlines are integer points and segments. An arc is an integer centre, an integer radius and two integer direction vectors for its end rays, as ANV stores it ([ANV, Planar integer geometry](02-anvil.md#planar-integer-geometry-anvil-planar)). Offsetting by an integer distance keeps the centre and rays and changes only the radius, so concentric clearances stay exact.

Only arc–arc and arc–line intersections snap, and they snap conservatively: fills inward and keep-outs outward. Three-point arcs from KiCad import convert under the same snap, and Bodies are derived on demand. The iOverlay library (MIT or Apache-2.0) gives integer polygon Booleans and buffering but subdivides round joins [iOverlay]. Clipper2 likewise offers integer Booleans and offsets without arcs [Clipper2]. `anvil-planar` adds exact arcs on the grid, and ANV decides whether iOverlay serves its straight-segment cases.

| Derived Body | Representation | Consumers | Error bound |
| --- | --- | --- | --- |
| Laminate | BRep: outline extruded, holes removed | MEC fit, Flux structural, STEP | Exact |
| Copper layer *n* | Planar BRep from tracks, pads and fills | DRC, Flux, 3D view | Exact; chords within a stated tolerance (default 0.5 µm) |
| Copper solid | Copper layer extruded by its thickness | Local 3D EM and thermal zooms | As above |
| Assembled board | Laminate plus part bodies at placements | MEC, STEP AP242, IDX | The parts' import bounds |
| Envelope | Box, cylinder or prism per part | Fast clearance | Declared, conservative |

Silkscreen revision, date and serial text are late-bound placeholders, filled at output and excluded from KLN's definition digest, so assigning a revision never makes a board look modified.

### One model with the enclosure

**Decision D-ELX-7:** The enclosure and the board live in one design repository and one Kiln graph, each able to drive the other's geometry; IDX serves only tools outside Crucible.
*Why:* every exchange step can go stale, and even Fusion, with both domains in one environment, raises cross-domain changes as alerts to synchronize [Fusion ECAD MCAD].
*Rejected:* an internal IDX-style baseline and increment protocol, which recreates the synchronization problem inside one product.

The guide example showed the outline and the USB connector following the enclosure. A `lock: mech` placement refuses drags; if referenced geometry disappears, the rebuild fails with a typed `ResolveError` and never keeps the old placement. Height limits arrive as keep-in volumes checked against the parts' 3D bodies. Multi-board systems follow the same rule: one Network and one Assembly, with mated connectors checked as [Networks](#several-boards-one-system) describes, and no system-level synchronization step.

### Boards from other tools

Enclosures are often designed around boards from other ECAD tools long before ELX's layout is in use. ECO imports IDF and STEP boards, which KiCad 9 exports [KiCad 9 PCB editor], as read-only board Parts in phase 2. In phase 1, MEC checks enclosures against boards imported as STEP assemblies. IDX V6 (December 2025) defers splines, 3D keep-outs and chamfered edges to V7 [prostep IDX forum], and its change proposals arrive as Proposals.

### Rigid-flex and folding

A flex region carries bend lines with radius, angle and order. `anvil::fold` maps it onto cylinders with the neutral-layer offset from the flex stackup, and folded copper follows the same map. Checks follow IPC-2223, current at revision E [IPC design standards]: minimum bend radius (larger for dynamic flexing), no vias in bend zones, staggered conductors and hatched planes.

Bend strain comes from a Flux laminate shell model as a `Field<Body, Strain>`, compared with the copper fatigue curve. The flat view feeds fabrication, and the enclosure assembly instantiates the folded view.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Stackup | Layers, Materials with laminate designations, `Tol` thicknesses, via spans, regions | `StackupError::UnsupportedSpan` naming the nearest span | ELX-O-BRD-1 | 3 |
| Fabrication and assembly classes | `fab_class` and `assembly_class`, Class 1 to 3/A, select pinned MFG rule packs | A class without a rule pack for the chosen fabricator is a typed error | ELX-O-BRD-1 | 3 |
| Layout geometry | Integer points, segments and centre-radius arcs; exact integer offsets of arcs. Requires: ANV `anvil::planar::offset` | A construction that leaves the grid snaps conservatively, never to nearest | ELX-O-BRD-1 | 3 |
| Board Bodies | Layout data to laminate, copper and assembled Bodies with bounds. Requires: ANV `anvil::planar::boolean` | A failed planar Boolean names its items; no partial board is returned | ELX-O-BRD-1 | 3 |
| Lifecycle placeholders | Revision, date and serial text late-bound at output | A placeholder outside a text item is a typed error | ELX-O-BRD-5 | 3 |
| Enclosure co-design | Outline, holes and placements as expressions of enclosure geometry; locks | `ResolveError` when referenced geometry disappears | ELX-O-BRD-2 | 3 |
| IDF and STEP board import | Read-only board Part with Instances, designators and keep-outs (ECO's reader, on an early 1.x train) | Unmapped items listed | ECO-O-26 | 2 |
| IDX V6 | Baseline import; export and change proposals as Proposals | Proposals conflicting with locks rejected item by item, with IDX responses | ELX-O-BRD-3 | 2 (baseline import), 4 |
| Rigid-flex regions | Per-region stackups and layer sets | An item in no region is a DRC error | ELX-O-LAY-1 | 4 |
| Fold | `anvil::fold` per bend line, in bend order. Requires: ANV `anvil::unfold`, `anvil::fold` | Radius below the rule fails; self-intersection reported with location | ELX-O-BRD-4 | 4 |
| Flex strain | Laminate strain Field per bend against the fatigue curve | Plastic copper strain flagged | ELX-O-BRD-4 | 4 |

## PCB layout

Layout is where most board time goes, so its tools must be fast under the pointer, exact in their verdicts and reviewable when an agent drives them. This section covers placement, design rules, DRC, routing, pours and the handoff to manufacturing.

### Placement

Interactive placement edits Instance `Transform`s in the `Layout` module: drag with live DRC, push, align, flip, arrays, rooms and channel replication by provenance. Network edits reach the board on the next rebuild with no annotation step. A removed Instance's orphaned tracks become DRC errors, never silent deletions.

Placement drag and the router run in the engine process on PLT's `Drag` pool lane ([PLT, Threads and pools](12-platform-performance.md#threads-and-pools)). Pointer updates arrive as literal overrides through AGT's `edit.stream`, which ends in one `edit.apply` that writes the Change. Kiln never writes a result computed under overrides to the shared cache.

**Decision D-ELX-8:** Automatic placement and routing are edit tools, never evaluation steps: each use writes ordinary `Layout` edits on a branch and opens a Proposal.
*Why:* evaluations stay fast and deterministic, agents iterate on reviewable diffs, and a GPU optimizer's rounding never reaches a check.
*Rejected:* placement or routing as Kiln-evaluated features, which would rewrite copper after every upstream edit.

Cypress (ISPD 2025, Apache-2.0) places parts by gradient descent on wirelength, electrostatic density and a net-crossing penalty, but lacks height, thermal and critical-net terms [Cypress paper]. The placer, a Wasm component, adopts Cypress's formulation and adds MEC's keep-in heights, thermal spreading, decoupling-loop length, critical-net proximity and designer locks. Its density solve calls `fft_solve` through `crucible:ops/flux`, and work is ordered by canonical numbers, never names. Targets: match Cypress's published results on its open suite, and place 500 parts in under 60 s on the reference laptop.

### Design rules and the constraint manager

Design rules are checks from `std::electronics::rules` in the design source, so they diff and merge like any code. The constraint manager is UIX's grid over them, and editing a cell rewrites the expression.

```
let hs  = net_class("ddr4_dq", nets: ddr.byte(0).dq + [ddr.byte(0).dm])
let bus = net_class("48v", nets: [p48v, p48v_rtn])               // Power range 0V..=60V
let iso = barrier("mains_to_selv", standard: iec_62368_1, insulation: Reinforced,
                  working_voltage: (peak: 420V, rms: 250V), ovc: Ovc.ii,
                  pollution: Pd.p2, material_group: Mg.iiia, altitude: 2000m)
board.rules([
    clearance(all, all) >= fab.min_space,                     // fabricator record
    clearance(bus, all) >= functional_spacing(bus),           // IPC-2221 package
    width(hs, layer: outer) == impedance_width(40ohm ± 10%),  // solved from the stackup
    delay_match(hs, to: ddr.byte(0).dqs, within: 5ps),
    max_vias(hs) <= 2,
    clearance(iso.sides) >= iso.clearance(),
    creepage(iso.sides) >= iso.creepage(),
])
```

**Decision D-ELX-9:** Rule precedence follows scope specificity, and an ambiguous overlap is an error that asks for an explicit `override`.
*Why:* a designer sees which rule applies to any object, and an agent cannot change behaviour by reordering rules.
*Rejected:* numeric priorities, which hide intent, as in Altium's query rules [Altium constraint manager]; a rule store beside the design, such as Altium's `Constraints.xml`.

Specificity runs from board default through layer, net class, class pair, net and net pair to object. The constraint manager shows winning and shadowed rules, and manufacturing limits come from MFG's rule packs.

**Decision D-ELX-28:** Spacing between nets that cross no safety barrier comes from `functional_spacing(nets)` over a licensed IPC-2221 package, at the nets' declared voltages.
*Why:* 24 V, 48 V and 100 V buses need voltage-dependent spacing that fabricator minimums omit, so designers would otherwise hand-write rules.
*Rejected:* fabricator minimums only; isolation barriers for functional voltages, which misstate the insulation.

IPC-2221's current revision is C [IPC design standards]. Its spacing categories cover internal conductors, uncoated external conductors below and above 3050 m, polymer-coated and conformally coated external conductors, and component leads [Pollex IPC material]. The board's altitude and coating select the column.

A `conformal_coating` board record names the material, thickness and keep-out regions over connectors and test points. It selects the coated columns, feeds MFG's assembly package, and fails test-point access where coating covers a probe site.

**Decision D-ELX-24:** Safety spacing comes from a declared isolation barrier: end-product standard, insulation grade, working voltages, overvoltage category, pollution degree, material group and altitude.
*Why:* end-product standards' tables differ from IEC 60664-1 alone, so spacing without grade, voltage form and altitude is wrong on safety-critical boards.
*Rejected:* a constructor from voltage and pollution degree only; one default standard.

Barrier tables are licensed data packages per standard edition, such as IEC 62368-1:2023 [IEC 62368-1], IEC 61010-1:2010 with AMD1:2016 [IEC 61010-1], and IEC 60601-1:2005 with AMD1:2012 and AMD2:2020 [IEC 60601-1]. Results carry the screening label, list the barriers checked, and apply slot and coating rules only where the standard permits.

**Decision D-ELX-30:** Standards and handbook tables are organization-licensed data packages, never std content, unless contract section 7.7 allows their licence.
*Why:* IPC, IEC, Telcordia and FIDES sell or register each copy, and FIDES needs registration [FIDES].
*Rejected:* bundling every table in std; a redistribution exception per publisher.

### DRC

DRC is a set of checks over derived copper and holes, run by a Wasm component on `anvil-planar`, so every platform reaches one verdict. Kiln caches tiles, and an edit re-checks its tiles plus neighbours within the largest clearance. Distances are exact, and 3D checks refine envelope Bodies only where they collide.

Each violation names the rule, the shadowed rules and both objects, and suggests a fix such as "move 0.04 mm". Targets: full DRC of a 20-layer, 10,000-net board under 10 s on the reference laptop; incremental DRC after a routing edit under 50 ms.

### Interactive routing

KiCad's router shoves in an iterative loop over obstacles, with walk-back fallbacks, spring-back nodes and post-shove optimization [KiCad PNS shove]. Crucible keeps that structure and changes three things:

1. **Exact geometry.** Decisions use integer predicates, so a shove that passes in the router passes DRC.
2. **Rule-aware cost.** Costs read the rule set, including delay budgets. A shove that would push a matched net out of its window is refused, with the reason at the cursor.
3. **Recorded sessions.** Every gesture is recorded with its inputs, and UIX replays ELX's sessions frame by frame.

Targets: under 16 ms per pointer update with up to 50 shoved items; finishing a route writes one Change within 50 ms.

### Length and delay tuning

Constraints may be stated in length or time, as KiCad 10 allows with per-layer profiles [KiCad 10 release], but Crucible computes delay from physics. A cached Flux solve per cross-section gives delay over frequency, and stackup tolerances make each net's delay a `Tol<Time>`, matched worst case. Via and package delays come from per-via solves and IBIS package data, and tuning patterns keep self-coupling under a stated limit.

### Autorouting

**Decision D-ELX-10:** The autorouter is a search-based public Wasm component: flow escape routing, negotiated-congestion global routing, gridless A* detail, rip-up and reroute, and via-minimizing cleanup.
*Why:* PCBWorld, an engine-grounded benchmark of 679 real boards, reports that learning-based routing still lags rule-based routers [PCBWorld].
*Rejected:* an end-to-end learned router, unproven and hard to review; linking Freerouting, which is GPL-3.0 [Freerouting] and stays an external baseline over Specctra DSN and SES.

Learned models may supply cost hints through a Wasm component interface but never decide legality. Global routing follows PathFinder, McMurchie and Ebeling's negotiated-congestion router from FPGA 1995 [PathFinder award]. Target: beat Freerouting's completion and via count on PCBWorld-Bench at equal or lower runtime.

Allegro X AI claims a 10× or greater turnaround reduction [Allegro X AI]. Quilter generates candidate boards by reinforcement learning under physics checks [Quilter]. Both claims are vendor-stated.

**Decision D-ELX-31:** Placer and autorouter work items open only after counsel's freedom-to-operate search of their code paths, and learned hints train only on licensed corpora.
*Why:* contract section 13.1 runs chain A's geometry in the same order, and PCBWorld states no licence for its corpus.
*Rejected:* building first and reviewing at release, which risks discarding finished work.

### Pours, planes and vias

**Decision D-ELX-11:** Zone fills are derived on every rebuild, never stored, and snap conservatively away from obstacles.
*Why:* a stale fill is a known way to ship shorts or missing connections, and integer clipping by tile makes fills reproducible and fast.
*Rejected:* stored fills refilled by hand before output.

- **Zones** have an outline, net, layers, priority, clearance, thermal reliefs, island policy and solid or hatched fill; equal-priority overlaps are an error.
- **Plane splits** are zones on plane layers; a check flags signals crossing a gap in their reference plane.
- **Vias** cover through, blind, buried, stacked and staggered microvias, via-in-pad, back-drilling with a stub rule, stitching and teardrops within the fabricator's HDI (high-density interconnect) limits.
- **Via protection.** Each via class declares `protection: Ipc4761Type`, one of IPC-4761's seven types from tented to filled and capped [LEITON IPC-4761]. The fabrication drawing states it, and a manufacturability rule checks it for via-in-pad.

### Test points and the manufacturing handoff

`test_point(net, pad:, side:, min_pitch:, keepout_height:)` adds probe access, and an automatic Proposal adds test points to nets without access.

MFG owns the factory handoff ([MFG, Electronics and harness manufacturing handoff](07-manufacturing.md#electronics-and-harness-manufacturing-handoff)), and ECO owns every format writer and its phase. IPC-2581C [IPC-2581C release], Gerber X2 and X3 at revision 2026.05 [Ucamco Gerber downloads], drill files, IPC-D-356 test netlists [IPC design standards] and ODB++ [Siemens ODB++] arrive in phase 3. Gerber X3 carries component data for assembly [Gerber X3 release]. KiCad 9's ODB++ export [KiCad 9 release] is an external oracle, and ELX shows writer findings, including IPC-2581C fabricator feedback [IPC-2581 Consortium], on the objects they name.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Interactive placement | Instance `Transform` edits with live DRC on the `Drag` pool lane through `edit.stream` | Overlaps shown live; the edit is allowed and flagged | ELX-O-LAY-3 | 3 |
| Automatic placement | Placer to a Proposal | Infeasible constraints named; a partial result is labelled partial | ELX-O-LAY-5 | 4 |
| Constraint manager | Grid over rule declarations with specificity precedence | Ambiguous overlap requires `override` | ELX-O-LAY-6 | 3 |
| Functional spacing | `functional_spacing(nets)` over a licensed IPC-2221 package; voltages from `Power` ranges and net classes | A net without a voltage range is a typed error naming it | ELX-O-LAY-6 | 3 |
| Conformal coating | `conformal_coating` record selects coated columns and keep-outs | A coated probe site fails test-point access | ELX-O-LAY-7 | 3 |
| Isolation barriers | Creepage and clearance per declared standard, grade and conditions | A barrier without a standard is an error | ELX-O-LAY-6 | 3 |
| DRC | Exact checks over derived geometry, incremental by tile. Requires: ANV `anvil::planar::distance` | Violation with rule, shadowed rules, objects and fix | ELX-O-LAY-1 | 3 |
| Interactive routing | Walkaround, shove, highlight; 45°, 90°, free angle and arcs; differential pairs; drag | The head stops at the last legal point and shows the blocker | ELX-O-LAY-3 | 3 |
| Multi-track routing and fanout | Group routing at rule pitch; BGA and QFN escape | Members that cannot follow stop separately; unescapable pins listed | ELX-O-LAY-3 | 4 |
| Delay tuning | Field-solved delay as `Tol<Time>`; tuning patterns | An unachievable match reports the shortfall | ELX-O-SI-1 | 3 |
| Autorouting | Router to a Proposal | Unrouted connections listed; no Proposal carries DRC errors | ELX-O-LAY-4 | 4 |
| Zones, fills and teardrops | Derived on every rebuild, conservatively snapped | Equal-priority overlap is an error; islands handled per policy | ELX-O-LAY-2 | 3 |
| Vias and HDI | Spans from the stackup and the fabricator record; `protection: Ipc4761Type` per class | A disallowed span or stack is refused with the rule; via-in-pad without a filled and capped type fails | ELX-O-LAY-1 | 3 (through, blind, buried), 4 (microvias, HDI) |
| Test points | `test_point` features; Proposals for nets without access | Untestable nets listed | ELX-O-LAY-7 | 3 |
| Board data for manufacturing | Board model read by ECO's writers, IPC-D-356 included, for MFG's packages; findings on board objects | A construct a writer cannot express is listed by that writer | ELX-O-DET-1 | 3 |

## Electrical analysis

A board that passes DRC can still ring, droop, radiate or overheat, so Crucible analyses the laid-out board itself, with its stackup, copper and parts. Every analysis is an Ingot feature that builds a Flux problem or calls a solver Wasm component. It returns Fields with an `ErrorBudget` and a `ValidityEnvelope` at `Interactive` or `SignOff` fidelity, and Kiln re-runs only the analyses an edit touches. Screening results carry a screening label and never stand as compliance.

[[DIAGRAM diagrams/08-electronics-analysis-dataflow.jsx: electrical analysis dataflow · 7 analyses from one board model]]

Read it left to right: board data feeds seven analyses that return Fields and checks, and the labelled arrows carry temperature and part power between them.

### Signal integrity

Impedance and per-length resistance, inductance, conductance and capacitance (RLGC) come from a 2D quasi-static Flux solve per cross-section, with conductor loss, roughness and causal dielectrics. The solve holds below a tenth of a wavelength. Post-layout extraction splits nets into lines, vias and discontinuities, crosstalk covers aggressors within a reported window, and S-parameters use Touchstone 2.1 [IBIS home]. Discontinuities that the quasi-static models cannot represent go to Flux's full-wave extraction, which contract section 13.4 places in phase 4.

Macromodels use vector fitting (Gustavsen and Semlyen, 1999) with residue perturbation for passivity, as the SINTEF toolbox does [SINTEF vector fitting]. Grivet-Talocia's Hamiltonian test checks passivity [Grivet-Talocia 2004], and fit error enters the `ErrorBudget`. Fitting runs on `linalg`, since faer runs only in `CpuIsa` (contract section 7.1) [faer sparse].

Channel simulation offers statistical eyes and bit-by-bit runs with IBIS 8.0 buffers, ratified on 5 December 2025 [IBIS 8.0], and IBIS-AMI equalization. IBIS-ISS is at 1.0, and the parser is validated against IBISCHK8 [IBIS home].

**Decision D-ELX-12:** IBIS-AMI executables run only as External Ops on untrusted-evaluation workers, in a pinned host image per vendor platform (contract section 7.8).
*Why:* AMI models are vendor-compiled native libraries that cannot be determinized, and an escape beside attestation keys would poison the shared cache.
*Rejected:* loading AMI libraries into the engine process; running them on trusted builders; accepting one untrusted run for a `SignOff` check.

Gates and `SignOff` checks accept an AMI result only when two single-use runs on different hosts give one `ObjectId` in signed receipts. A nondeterministic model yields `Unverified` results, which meet a gate only under a policy allowance. Releases pin result `ObjectId`s, and a missing platform build is reported, never emulated.

**Compliance kits.** High-speed designers run standard compliance kits: DDR4 and DDR5 eye masks and timing budgets, and PCIe and USB channel compliance. HyperLynx, for example, offers "standards-based compliance analysis" for DDR and SerDes links [HyperLynx]. `std::electronics::compliance` ships one package per standard edition, each a set of checks over ELX's channel results; the limit tables are licensed data under the standards-licensing decision (D-ELX-30). The IEEE 802.3ck contributed channels and COM tool serve as the first reference [IEEE 802.3ck tools].

### Power integrity

Target impedance per rail is the allowed ripple divided by the transient current. The power-delivery network (PDN) impedance comes from Flux's plane-pair cavity model ([FLX, Electromagnetics](03-flux.md#electromagnetics)). It solves a 2D Helmholtz problem on each pair of sheet Bodies, with port, via, capacitor and regulator elements, using Flux's indefinite solvers. Above the plane-pair limit, a full-wave solve is suggested.

Decoupling optimization picks capacitor types, counts and sites by greedy insertion and local search. IR drop solves DC conduction on per-layer copper sheets joined by via and plating resistances, using Flux's layered sheets. A current-capacity screen follows IPC-2152, still current in its original revision [IPC design standards].

Electro-thermal coupling is phase 4 (contract section 13.4): Flux uses monolithic Newton with continuation and reports `Runaway { power }` at the turning point.

### Parasitic extraction for power electronics

Power-electronics layouts live or die by their parasitics: the inductance of the hot loop, a busbar's AC resistance, a module's coupling capacitance. Ansys Q3D, the incumbent, extracts frequency-dependent RLCG from busbars and inverter modules and generates an equivalent SPICE model [Ansys Q3D].

FLX owns `flux::extract_rlcg(bodies, terminals, band)`: magnetoquasistatic solves for partial inductance and AC resistance and electrostatic solves for capacitance, returning `Field<(Ports, Ports, Frequency), Complex<Impedance>>` with error budgets (contract section 13.4, phase 4). ELX turns the result into a passive SPICE subcircuit by the same vector fitting and passivity enforcement it uses for S-parameters, and the fit error joins the budget. The subcircuit drops into the converter's `Network` as one element, so switch-node overshoot and EMI (electromagnetic interference) filters see the real layout.

### EMC and EMI

ELX builds excitations and geometry for electromagnetic compatibility (EMC) screening; Flux solves the fields.

- **Radiated emissions.** Common- and differential-mode currents become current Fields on copper. Flux's FDTD (finite-difference time-domain) solver computes far fields at 3 m or 10 m with the enclosure, cables and harness in the model.
- **Conducted emissions.** A line impedance stabilization network (LISN) sits in the simulation, with hot-loop parasitics from the extraction above.
- **Immunity and ESD.** Port-level transient injections rank vulnerable nets.
- **Rule screening.** Every rebuild checks return-path breaks, slots under clocks, unstitched plane edges, long stubs and missing ground vias.

### Board thermal

Part power comes from simulation averaged over a stated window, a declared operating mode or datasheet values, labelled by source. Packages use two-resistor (JESD15-3) or DELPHI (JESD15-4) compact models [NISTIR 7648], or the full package Body.

**Decision D-ELX-26:** At `Interactive` the board uses orthotropic conductivity per layer and tile from copper coverage; at `SignOff` it uses 2.5D layered conduction, per-layer thin sheets plus through-plane conductance, sharing the IR-drop machinery.
*Why:* 35 µm copper on a 100 mm board is a 3,000:1 scale ratio over thousands of traces, which no volumetric octree resolves.
*Rejected:* explicit copper for the whole board; effective conductivity at `SignOff`, which hides hot spots under thin traces.

Explicit 3D copper serves only local zooms. Convection and the enclosure come from Flux conjugate heat transfer, laminar in phase 3 and turbulent in phase 4 (contract section 13.4). Outputs are a `Field<Body, Temperature>` and junction temperatures as a `Field<Instances, Temperature>`. Checks compare them with limits and derating rules, and they feed back to simulation and IR drop.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Impedance and RLGC | Cross-section solve to `Field<Frequency, Rlgc>` with tolerance bands | Beyond the quasi-TEM limit flagged; a dielectric without frequency data names the Material | ELX-O-SI-1 | 3 |
| Post-layout extraction and crosstalk | Nets to S-parameters per net group; NEXT and FEXT within a reported window; full-wave for unmodelled discontinuities | An unmodelled discontinuity is sent to full-wave extraction with its cost reported | ELX-O-SI-1 | 4 |
| S-parameter macromodels | Touchstone data through ECO's codec; vector fitting with passivity enforcement | Non-passive or non-causal data flagged per frequency; failed fit reports its worst error | ELX-O-SI-2 | 4 |
| Pre-layout topology and channels | Topologies and routed nets to eyes, timing and BER contours; AMI results accepted on matching receipts | A non-linear channel in statistical mode is refused; a missing AMI build is reported | ELX-O-SI-3 | 4 |
| Interface compliance kits | `std::electronics::compliance` packages per standard edition (DDR, PCIe, USB) as checks over channel results | A kit without its licensed limit table leaves its checks `Undecided` naming the table | ELX-O-SI-4 | 4 |
| Target impedance and PDN | Masks per rail; plane-pair cavity model with capacitor, via and regulator elements | Missing load data leaves the check `Undecided`; beyond the plane-pair limit flagged | ELX-O-PI-1 | 4 |
| Decoupling optimization | Proposal with placements and impedance before and after | An infeasible mask reports the best achievable impedance and failing band | ELX-O-PI-1 | 4 |
| IR drop and current capacity | Thin-sheet DC conduction per layer; IPC-2152 screen. Requires: FLX Layered sheets | Limit exceeded fails with location, value and limit | ELX-O-PI-1 | 3 |
| Electro-thermal coupling | Monolithic Newton with continuation (FLX) | `Runaway { power }` at the turning point | ELX-O-PI-2 | 4 |
| Extracted parasitics as subcircuits | `flux::extract_rlcg` results fitted to passive SPICE subcircuits used as Network elements | Fit error above the stated bound fails with the worst frequency | ELX-O-PWR-1 | 4 |
| Emissions screening | Current Fields to far fields against limit lines; conducted emissions with a LISN model. Requires: FLX FDTD | Screening label; a missing cable or enclosure is listed as an assumption | ELX-O-EMC-1 | 4 |
| Immunity and ESD screening | Ranked vulnerable nets | Screening label; an injection outside a port's model range is flagged | ELX-O-EMC-1 | 5 |
| Return-path and EMC rule screening | Geometric checks on every rebuild | Violations with locations | ELX-O-EMC-1 | 3 |
| Board thermal | Part power to temperature and junction Fields. Requires: FLX Layered sheets | Estimated power labelled; a part without a thermal model uses θJA with a warning | ELX-O-TH-1 | 3 |

## Analog and mixed-signal simulation

Engineers judge a simulator by whether it converges, whether the vendor's models run on their own laptop, and whether its numbers can be trusted. This section defines Crucible's own engine, how vendor models qualify to run in it, what each result's error budget contains, and the specialised analyses for switching converters and mixed-signal boards.

### The engine

**Decision D-ELX-13:** Crucible's circuit simulator is a set of Rust Flux operations: modified nodal analysis, Newton with homotopy fallbacks, and BDF or trapezoidal integration.
*Why:* it must run in Wasm with Flux's Fields and adjoints, faer breaks the canonical class, and junction currents need `f64`.
*Rejected:* linking ngspice, whose LGPL and GPL-2+ files and lack of derivatives and Wasm parity rule it out [ngspice copyright]; VACASK and Xyce, under AGPL and GPL; `f32` GPU batching.

The simulator factors with Flux's block-triangular LU in `linalg`, the KLU scheme reimplemented. Analyses are `F64Required`, and Monte Carlo runs one sample per CPU SIMD lane. SPICE3 device models (diode, Gummel-Poon BJT, JFET, MOSFET levels 1 to 3, VDMOS) are ported from ngspice's BSD-3-Clause files with attribution. Each is enabled after matching ngspice on a regression corpus. The engines Crucible measures itself against are listed under [Reference](#simulation-engines).

**Decision D-ELX-14:** Crucible's Verilog-A front end, a public Wasm component, lowers compact models to the shared kernel IR (contract section 7.5).
*Why:* BSIM, PSP, VBIC and many vendor models ship as Verilog-A, and one IR gives native speed, browser parity and a fixed operation order.
*Rejected:* OSDI shared objects, native and platform-specific; Wasm-only device models, which lose derivatives and the fixed order.

Verilog-A constructs join the IR in phase 3. The front end emits canonical CPU and Wasm kernels with derivative Jacobians, keyed by source, front-end version and target.

### Vendor models on every laptop

Converter and analog work runs on manufacturers' PSpice and LTspice models, and LTspice or KiCad run them locally in seconds. ngspice states that PSpice and LTspice device model parameters and netlists can be applied for discrete circuits [ngspice home]. Crucible must match that on a laptop, offline, without a server round trip.

**Decision D-ELX-25:** The native engine runs every unencrypted vendor model, in PSpice or LTspice dialect with behavioural sources, that passes a differential check against ngspice. ngspice stays the reference and fallback, and encrypted models run only in vendor engines an organization registers.
*Why:* designers judge a simulator by whether vendor models run, and ngspice has added PSpice and LTspice compatibility over many releases [ngspice news]. A differential check lets laptops simulate locally while ngspice keeps native results honest.
*Rejected:* running every vendor model in ngspice as an External Op, which needs a server for each run; listing dialect constructs as unsupported until a manual port; decrypting models; shipping vendor engines.

1. **First use.** A model the native engine has not seen runs once on its own test bench in both engines. The check runs in CI or on the team server, never on the laptop, because ngspice is an External Op (contract section 7.8).
2. **Qualification.** Agreement within the bench's tolerance records the model's `ObjectId` as native-qualified in a pinned record; disagreement keeps it on ngspice and lists the differing waveforms.
3. **Daily use.** Qualified models run natively everywhere, browsers included, at full speed.
4. **Offline and unqualified.** A desktop may run ngspice locally in an OS sandbox with egress denied. Its results are `Unverified`, at most `Interactive`, never cached and never gate-deciding (contract section 7.8).

The target is 90% of the unencrypted vendor corpus (TI, ADI, Infineon, onsemi and ST power and analog models) native-qualified at the phase 3 gate. For an encrypted model, the organization supplies the host image, accepts its batch-use terms and declares licence-server egress for an administrator to grant. That host receives only inputs labelled at most `internal` without `controls`, unless a two-person grant names it. Gates accept ngspice and vendor-engine results on matching receipts, as for AMI results.

### Analyses and their error budgets

Every simulation result carries an `ErrorBudget`, and each part names how it was bounded, so a check never passes on an unlabelled estimate (contract section 5.1):

| Error source | How it is bounded | Bound kind |
| --- | --- | --- |
| Algebraic | Newton residual scaled by a condition estimate | `Estimated { Class }` under the calibration class `mna_newton`, measured on ELX's simulation corpus by FLX's calibration machinery; outside the class's envelope (condition estimate, contraction rate) it is `Indicator` |
| Temporal | Adjoint-weighted estimate for the checked goal, or step-halving with frozen breakpoints | `Estimated { Class }` when either runs; summed local truncation errors alone are `Indicator` |
| Input and tolerance | `Tol` propagation, worst case by affine forms | `Guaranteed` for the propagation itself |
| Statistical | Monte Carlo yield and percentiles | `Estimated { Statistical }`: Clopper–Pearson intervals for yield, order-statistic intervals for percentiles, each at a stated α |
| Model form | A device envelope citing a validated bound, or a policy allowance | `NotQuantified` otherwise |

The temporal rule exists because phase error accumulates in oscillators, LC tanks, phase-locked loops and switching converters, so summed local errors understate it; it follows [FLX, Time integration](03-flux.md#time-integration). When model form is `NotQuantified`, a check's verdict is `Undecided { reason: Unquantified(ModelForm) }` unless a policy allowance quantifies it (contract section 5.6).

Monte Carlo draws from `Tol` distributions with ING's correlation groups, so parts from one reel move together. Random streams come from KLN's counter-based streams, keyed by sample index, never by class, fidelity or names (contract section 7.2). Added samples never change earlier ones. Targets: C6288 with PSP103.4 models within 1.2× of VACASK's time; 10,000 samples of a 200-node circuit's AC response in under 60 s on the reference laptop.

### Switched transients for converters and drives

Converter and drive designers simulate control loops over thousands of switching periods. Device-level transients are far too slow for that, and averaged models miss ripple and switching losses. PLECS reduces power semiconductors to ideal switches, so a switching event "requires just two steps" [PLECS].

**Decision D-ELX-34:** `switched_transient(network)` simulates converters with ideal-switch elements, per-topology state matrices cached by Flux's per-mode compilation, exact event location, and losses from lookup tables.
*Why:* each switching event then costs two linear solves, which makes closed-loop runs over thousands of periods practical while losses still come from the parts' switching-energy data.
*Rejected:* averaged models only, which miss ripple and per-cycle losses; device-level BDF for every loop run, orders of magnitude slower.

Its temporal error follows the same rule as other transients. The target is 50 times the speed of a device-level transient on a buck converter and a three-phase inverter, with waveforms agreeing within the loss tables' tolerance.

### Mixed-signal

An event-driven digital kernel in the style of XSPICE provides four-state logic with threshold and hysteresis bridges, and digital events become analog breakpoints. Verilog blocks compile with Verilator (LGPL-3.0 or Artistic-2.0 [Verilator]) and run as External Ops; microcontrollers run real firmware in Renode, as [Firmware and the bench](#firmware-and-the-bench) describes.

### Reliability prediction and derating

Reliability prediction gives failure rates for comparison and allocation, and every result names its handbook, because handbooks disagree by large factors. FIDES is the default for new designs. Telcordia SR-332, MIL-HDBK-217F and IEC 61709 through SN 29500 serve telecom, defence and industrial users, and physics-of-failure models cover critical joints (handbooks under [Reference](#reliability-handbooks)).

Crucible ships the engines, and handbook tables are licensed data packages under the standards-licensing decision (D-ELX-30). Mission profiles are Ingot values, so part stresses per phase come from simulation and thermal results. Derating follows ECSS-Q-ST-30-11C Rev.2 of 23 June 2021 [ECSS derating], and fault trees from the `Network` hierarchy feed FMEA tables in `std::systems`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operating point | Newton with damping; gmin, source stepping and pseudo-transient homotopy in order. Requires: FLX Block-triangular sparse LU | Non-convergence returns the largest-residual nodes and a fix, such as a missing DC path | ELX-O-SIM-1 | 3 |
| DC sweep | Continuation over a source value to `Field<(Ports, Voltage), Current>` | As operating point, per point | ELX-O-SIM-1 | 3 |
| AC and noise | Linearized complex LU per frequency to `Field<(Ports, Frequency), Complex<Voltage>>`; adjoint noise | A singular matrix names the floating node set | ELX-O-SIM-1 | 3 |
| Transient | BDF and trapezoidal with LTE control, breakpoints and ringing detection, to `Field<(Ports, Time), Voltage>`; temporal error `Indicator` unless adjoint-weighted or step-halving verified. Requires: FLX `flux::solve_dae` | `StepTooSmall` with time, device and nodes | ELX-O-SIM-1 | 3 |
| Error budget labels | Algebraic part under class `mna_newton`; statistical parts with their method and α | A result outside the class envelope reports `Indicator` with the envelope variable | ELX-O-SIM-1 | 3 |
| Pole-zero and loop stability | Generalized eigenvalues; loop gain by Middlebrook's method [Middlebrook 1975] or Tian's [Tian et al. 2001]; margins | As AC | ELX-O-SIM-1 | 3 |
| Monte Carlo and corners | `Tol` samples with correlation groups, one per SIMD lane | Failed samples counted and reported, never dropped | ELX-O-SIM-4 | 3 |
| Sensitivity and worst case | Adjoint DC, AC and transient sensitivities; corner search confirmed by simulation | A non-differentiable point (switch event, limiter) is reported with its time and element | ELX-O-SIM-4 | 4 |
| Periodic steady state and harmonic balance | Shooting Newton; harmonic balance for mixers and amplifiers | Divergence with iteration history | ELX-O-SIM-1 | 5 |
| Vendor models | Native PSpice and LTspice dialects and behavioural sources; differential qualification against ngspice; encrypted models in organization-registered engines | A failed qualification lists the differing waveforms and keeps ngspice; host failure is a `Failure` with the host log; differing receipts give `Unverified` | ELX-O-SIM-2 | 3 |
| Verilog-A compact models | Front end to the kernel IR | Unsupported construct listed with file and line | ELX-O-SIM-3 | 3 |
| Switched transient | `switched_transient(network)` with ideal switches, cached per-topology matrices, exact events and loss tables | A topology with an algebraic loop of ideal switches is a typed error naming the switches | ELX-O-SIM-6 | 4 |
| Mixed-signal | Event kernel and bridges; Verilator External Ops | Unsupported HDL construct listed | ELX-O-SIM-5 | 4 |
| Reliability and derating | Handbook engines over licensed tables; physics of failure; mission profiles | A missing table leaves the check `Undecided` with the reason | ELX-O-REL-1 | 4 |

## Mechatronics

Motors, actuators and sensors join electrical and mechanical design, and GP6's drone depends on all three. This section defines machines at three model levels, actuators, sensors and drives, each a `Network` element so that a drive simulation changes model level without rewiring.

### Electric machines

Machines come at three model levels (COV's L0 to L3 scale of physical form), each a `Network` element with rotational and electrical ports:

| Model level | Model | Use |
| --- | --- | --- |
| L1 lumped | dq model with flux-linkage saturation tables over (id, iq, θ), iron-loss resistance, thermal network | Systems and controls |
| L2 reduced map | Flux-linkage, torque and loss maps from batched Flux magnetostatic solves | Drive design, efficiency maps, tuning |
| L3 field | Transient magnetodynamics with motion and eddy currents, coupled to the drive Network | `SignOff`: ripple, cogging, losses, demagnetization |

Machine features build laminations, slots, star-of-slots windings and magnets for permanent-magnet, induction, reluctance, axial-flux and linear machines. Pyleecan is Apache-2.0 but couples to FEMM, which it supports only on Windows [Pyleecan], so Crucible solves machine magnetics in Flux.

**Decision D-ELX-16:** Efficiency and loss maps come from Flux magnetostatic solves per (id, iq) point, with motion through Flux's sliding interface or mortar coupling, and points solve in parallel and cache individually.
*Why:* map points are independent, so Kiln reuses every point after an edit that changes only the control strategy.
*Rejected:* analytic machine models only, which miss saturation and slot effects; one transient solve per operating point, far costlier than a map needs.

Solenoids and voice coils use magnetostatic force maps; piezo stacks use Flux's piezoelectric model with a Butterworth-Van Dyke lumped equivalent from phase 5.

### Sensors, drives and loads

A sensor has three layers: optional Flux transduction physics, a behavioural element (transfer, noise, drift, quantization) and a register interface. Register maps come from CMSIS-SVD or SystemRDL, and Renode generates peripheral stubs from SystemRDL and register tags from SVD [Renode peripherals]. The sensor's error budget is a check over the three layers, such as encoder angle error under 0.1°.

Inverters range from averaged models to switching models with losses from catalog switching-energy curves, and the switched transient serves closed-loop runs. Drivetrain elements let GP3's gearbox and ideal sources form one drivetrain from phase 2, with a lumped motor from phase 3.

A propeller is a rotational load element whose torque and thrust come from a map over shaft speed and inflow. The map comes from FLX and COV's rotor aerodynamics: blade-element momentum theory at L1, and rotating-domain flow at L3 in phase 4 ([COV, Aerospace](04-coverage.md#aerospace)). GP6's motor, ESC and battery then see the propeller's real load.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Machine geometry features | Typed parameters to machine Bodies and winding layout | Slot overlap or negative tooth width is a typed error | ELX-O-MCH-1 | 4 |
| Lumped machine model | dq element with saturation tables | Operation outside the tables is flagged, never extrapolated | ELX-O-MCH-1 | 4 |
| Flux-linkage, torque and loss maps | Batched magnetostatic solves with interpolation error | Unconverged points marked in the map | ELX-O-MCH-1 | 4 |
| Transient machine `SignOff` | Magnetodynamics with motion coupled to the drive Network. Requires: FLX Magnetodynamics with motion | Divergence reported with time and region | ELX-O-MCH-1 | 4 |
| Actuators | Force maps and lumped equivalents (4); piezo stacks (5) | Unconverged force-map points marked, as for machine maps | ELX-O-MCH-2 | 4, 5 |
| Sensor models | Three layers with an error budget as a check | A missing layer leaves the budget `Undecided` | ELX-O-MCH-2 | 4 |
| Drive models | Averaged and switching inverters with losses | Missing switching curves listed | ELX-O-MCH-2 | 4 |
| Propeller load | Rotational element over a thrust and torque map from rotor aerodynamics | Operation outside the map's speed and inflow range is flagged | ELX-O-MCH-2 | 4 |
| Drivetrain coupling | Drivetrain elements with ideal sources (2) or a lumped DC motor (3) in one Network | Port domain mismatch is a compile error | ELX-O-NET-3 | 2, 3 |

## System simulation and control

System engineers model whole machines as networks of components, design their controllers and exchange models with partners, and today they use Dymola, Amesim, Simulink and MATLAB for it. This section gives them those tools inside the same design: control representations, fluid and thermal element libraries, Modelica models as source, and co-simulation.

### Control representations and design

Control design uses plain Ingot values, with no separate block-diagram language:

| Representation | Type | Operations |
| --- | --- | --- |
| Transfer function | `Tf<In, Out>` over s or z, `Quantity` coefficients | Feedback, discretization (ZOH, FOH, Tustin), minimal realization |
| State space | `Ss<In, Out>` with typed signals | Controllability, observability, balanced truncation |
| Frequency response | `Zpk`; `Field<(Ports, Frequency), Complex<Ratio>>` for measured data | Bode, Nyquist, Nichols, margins |
| Block diagram and hybrid | A `Network` of signal ports; state machines with typed events | Flattening to state space; event detection |

A gain from a position error in metres to a torque has type `Quantity<Torque / Length>`, so a missing conversion fails at compile time. Plants come from Networks, reduced Flux models and Flux multibody models of MEC assemblies, linearized by `flux::linearize_multibody`. A Flux structural mode becomes a plant pole pair, so GP6's attitude loop is checked against frame resonances.

Design tools match what MATLAB's Control System Toolbox offers, PID tuning and LQR, LQG and Kalman design among them [MathWorks Control], with units checked. Controllers export as C with a harness that matches the Ingot reference bit for bit, and the code is a Software item.

### Fluid and thermal element libraries

Pack coolant loops, hydraulic actuation and refrigerant circuits are system models too. Amesim users rely on libraries for hydraulic, pneumatic and thermal components, heat exchangers and refrigerant loops among them [Amesim domains].

**Decision D-ELX-35:** `std::systems::fluid` provides hydraulic, pneumatic and thermofluid element libraries with stream connectors (pressure and enthalpy across, mass and enthalpy flow through) and CoolProp fluid properties.
*Why:* GP6 and GP12 cooling and every actuation system need these elements, and stream connectors carry enthalpy transport correctly when flow reverses at a junction.
*Rejected:* plain across-and-through ports without enthalpy transport, which mix temperatures wrongly at junctions; leaving fluids to an external tool through FMUs, which hides them from checks and adjoints.

CoolProp is an MIT-licensed thermophysical property library [CoolProp]; it enters through the native-code register or a Rust port, as contract section 12 requires. The libraries come in two steps:

- **Phase 4:** hydraulic elements: pumps, spool, poppet, check and relief valves, accumulators, cylinders, and pipes with compressibility and cavitation. Single-phase coolant elements join them (pipes, cold plates, effectiveness-NTU heat exchangers) for GP6 and GP12 cooling.
- **Phase 5:** two-phase thermofluid elements (evaporators, condensers, expansion valves, compressors) and pneumatic elements.

COV adds the envelopes, such as cavitation and choking flags, and the ladder from 1D pipes to FLX's 3D flow ([COV, Fluids](04-coverage.md#fluids)).

### Modelica models as source

Modelica users bring models as source: the Modelica Standard Library, at v4.1.0 under BSD-3-Clause, spans mechanical, electrical, magnetic, thermal, fluid and control components [Modelica Standard Library]. Dymola is built on this "object-oriented language for physical modeling" [Dymola].

**Decision D-ELX-36:** Modelica models enter as source through ECO's Modelica reader, which translates a declared subset into `network { … }` Ingot over ELX's element libraries; constructs outside the subset stay an FMU with `Untranslated { construct }`.
*Why:* translated models can be edited, versioned, diffed, optimized with Crucible's adjoints and checked like any Network, and Flux's compiler already does the index reduction and tearing a Modelica tool does.
*Rejected:* Modelica only through compiled FMUs, which keeps users in a second tool for every change; OpenModelica as a linked compiler, which is AGPL-3.0 for non-members [OSMC-PL 1.8].

The reader is ECO's, in phase 4 ([ECO, Simulation and analysis](11-interop-ecosystem.md#simulation-and-analysis)). ELX's part is the element libraries the reader targets, and a coverage target. By phase 5, 80% of the MSL example models in `Modelica.Electrical`, `Mechanics.Rotational`, `Mechanics.Translational` and `Thermal.HeatTransfer` translate and match the MSL reference results. Rumoca, an Apache-2.0 Rust Modelica compiler its authors call rough-edged [Rumoca], is a candidate for the reader's front end. Flux's Network compiler follows ModelingToolkit [ModelingToolkit].

### Co-simulation

**Decision D-ELX-17:** An FMU instance is a `Network` element with ports and units from its model description, run by Flux's FMI and SSP runtime.
*Why:* one runtime serves every FMU, while FMUs still join drives and plants through ordinary `connect`.
*Rejected:* a second FMI master in ELX; FMUs outside the Network model.

Flux's runtime implements FMI 3.0.2 [FMI 3.0.2 release] and SSP 2.0.1 [SSP 2.0 release], and FMU export and SSP are phase 4 (contract section 13.4). ELX owns bus simulation over FMI-LS-BUS. FMI-LS-BUS 1.0 (21 July 2025) covers the CAN family [FMI-LS-BUS 1.0], a 1.1 beta adds FlexRay and Ethernet, and a 1.3 beta adds LIN [FMI news]. Its demo FMUs cover CAN and FlexRay [FMI-LS-BUS examples].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Transfer-function and state-space algebra | Typed signals, discretization, realization | Unit mismatch around a loop is a compile error | ELX-O-CTL-1 | 4 |
| Linearization | Exact Jacobians of Network plants through Flux derivatives and of multibody plants through `flux::linearize_multibody`. Requires: FLX `flux::linearize_multibody` | A non-smooth operating point (contact, saturation) is flagged | ELX-O-CTL-1 | 4 |
| PID tuning | Constrained optimization of a margin objective over a stated uncertainty set | Infeasible margins: the best achieved margins are reported | ELX-O-CTL-1 | 4 |
| LQR, LQG and Kalman filters | Schur-method Riccati solvers on `linalg` | Uncontrollable or undetectable modes reported | ELX-O-CTL-1 | 4 |
| System identification | Prediction-error and subspace (N4SID) methods | Poor fit reported with residual whiteness tests | ELX-O-CTL-1 | 4 |
| Model order reduction | Balanced truncation with an a priori H∞ bound; Krylov for large plants | A reduced order that misses the requested bound reports the bound achieved | ELX-O-CTL-1 | 4 |
| H∞ and µ synthesis | Structured H∞ by nonsmooth optimization; LMIs through a conic solver | Infeasible bound: best achieved norm reported | ELX-O-CTL-1 | 5 |
| Model predictive control | Condensed or sparse QP through Clarabel (Apache-2.0 [Clarabel.rs]) or ADMM | Infeasible QP reported with active constraints | ELX-O-CTL-1 | 5 |
| Controller code generation | Fixed- or floating-point C with a bit-exact harness; a Software item | Overflow reported with signal and input | ELX-O-CTL-1 | 4 |
| Hydraulic and coolant elements | `std::systems::fluid` single-phase hydraulic and coolant elements with stream connectors and CoolProp media | Operation outside a medium's property range is flagged; a cavitating element sets its flag | ELX-O-FLD-1 | 4 |
| Two-phase and pneumatic elements | Two-phase thermofluid and pneumatic elements | As above, with choking flagged | ELX-O-FLD-1 | 5 |
| Modelica translation coverage | Element libraries the reader targets; coverage of MSL examples measured | An untranslated construct stays an FMU with `Untranslated { construct }` | ELX-O-CTL-3 | 4 |
| FMU elements | FMU instance as a Network element (FLX runtime). Requires: FLX FMU import (all three interface types) | Unmappable unit or variability is a typed import error | ELX-O-CTL-2 | 4 |
| Bus simulation | FMI-LS-BUS for the CAN family; LIN and Ethernet as the standard matures | Unsupported bus features reported | ELX-O-CTL-2 | 5 |

## Firmware and the bench

A board is not done until its firmware runs on it, and flashing a motor controller can start a motor. This section covers firmware as a released item, firmware-in-the-loop simulation, hardware-in-the-loop tests and flashing, with the human Approval that physical effects need.

### Firmware as a BOM item

A Software item (contract section 2) records its item number, version, binary hashes, source repository and Change, and toolchain. Its software bill of materials is SPDX 3.0 [SPDX specifications] or CycloneDX 1.7 [CycloneDX].

Its `ItemDefinition` holds the binary hashes, the software bill of materials digest, the `load` bindings and the toolchain digest (contract section 5.6). A release's approval subject covers that definition, so swapping a binary after approval voids the Approval.

1. **Binding.** A `load` relation binds a Software item to a programmable Instance per configuration, and the BOM lists it under the programmed assembly.
2. **Hardware contract.** Crucible generates a board description (pins, peripherals, clocks, memory map) as a Zephyr devicetree overlay or a Rust board-support crate. Firmware declares the description hash it was built against, and a check compares it: "Firmware 1.4.2 expects the status LED on PA5; board revision C routes it to PB3."
3. **Reproducibility.** CI rebuilds firmware in a pinned container as an External Op; a hash mismatch fails the release check.
4. **Release.** A signed release records board revisions, Software item versions and their compatibility matrix.

### Firmware-in-the-loop

**Decision D-ELX-18:** Renode is the default firmware emulator and QEMU the alternative for application processors, both as External Ops on untrusted-evaluation workers.
*Why:* Renode is MIT and runs unmodified Arm, RISC-V, x86 and Xtensa binaries [Renode], and firmware is untrusted code kept away from attestation keys.
*Rejected:* a Crucible emulator, duplicating a mature effort; single-family vendor simulators; emulators in the engine process.

Renode models multi-node networks and co-simulates RTL through Verilator [Renode RTL co-simulation]. Renode publishes Linux x86-64 and ARM64, Apple-silicon macOS and Windows packages (1.17.0) [Renode releases], so firmware runs on both server architectures, and ELX-O-FW-1 runs on each.

1. **Peripheral bridge.** Pins, ADCs, timers, PWM and serial buses map to nets or signal ports from the pin facet and board description, checked every rebuild.
2. **Lock-step time.** Emulator and network advance in quanta (default 10 µs). PWM edges and ADC samples cross as timestamped events, and results report the quantum's timing error.
3. **Determinism.** With fixed quantum, seeds and peripheral models, runs repeat, and the ELF hash enters the key. ELX-O-FW-1 checks repeatability per Renode release, and a run that differs on repeat is `Unverified` (contract section 7.8).
4. **Tests.** DWARF variables appear beside circuit signals, and firmware tests are checks, such as `require(settle_time(motor.speed, to: 3000rpm, within: 2%) < 150ms, name: "speed_settle")`.

### Hardware-in-the-loop

Real-time execution lies outside Kiln: plants export as FMUs or fixed-step C, and benches run as KLN's enrolled rig runners talking to `api` ([KLN, Physical tests and Evidence records](05-kiln-repo-plm.md#physical-tests-and-evidence-records)). A run produces an Evidence record signed with a TPM-held device key, never a cached result. The record is pinned in `ingot.lock` under `[[evidence]]` by the `CheckId` it serves, so one Change fixes every outcome (contract section 5.6).

### Flashing

**Decision D-ELX-29:** Every client flashes a board only through the transfer Act `flash_device` or inside a `bench_session` (contract section 7.6).
*Why:* firmware runs when the core leaves reset, so flashing a motor controller, ESC, heater driver or charger can start motion or release energy.
*Rejected:* flashing outside Crucible's record; flashing as an ordinary write, which would start devices without an Approval.

1. **Plan.** It names the Software item version, image digest, target board serial, and probe or bootloader.
2. **Write.** The bench adapter or gateway writes the image and reads back its digest. The target stays halted or held in reset until a person at the bench releases it.
3. **Approval.** It covers the image digest and target. The approval page lists the board's Network hazards (rotational ports, heaters, high voltage) with a "remove propellers and loads" step.
4. **Clients.** Client flashing runs only in code that verifies the Approval. In browsers it runs on the approval origin page after the ceremony. That page holds the WebUSB grant and checks the image's SHA-256 against the approved plan; the main web origin never holds a WebUSB grant. On desktops it runs in `apps/platform-*`'s flashing service, which verifies the Approval signature against the pinned approver directory. On a rig under `unattended_safe`, `run_rig_test` covers flashing.

Embedded developers flash dozens of times an hour, so one Approval per image would push them to their own probe tools and the record would never be written.

A `bench_session` is one AAL3 Approval that covers a bench for at most 8 h (contract section 7.6). It names the person at the bench, the board serial, the probe, one Software item lineage on one branch, a maximum count and the board's hazard acknowledgements. Flashes inside the session need no further Approval but keep read-back, hold in reset and the canonical hash. The session ends early on expiry, on a hazard change in the Network, or on an image outside the lineage. Agents never open or extend one, and the approval page lists every flash afterwards.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Software items | Hashes, software bill of materials and `load` bindings in the `ItemDefinition` | A board-description mismatch fails the release check; a binary swap voids the Approval | ELX-O-SYS-3 | 3 |
| Firmware reproducibility | Pinned-container rebuild and hash comparison | A mismatch fails the release | ELX-O-SYS-3 | 4 |
| Firmware-in-the-loop | ELF and board description to traces and checks, in lock-step, on x86-64 and ARM64 workers | Pin-map mismatch is a `Failure`; an unsupported peripheral refuses the run | ELX-O-FW-1 | 4 |
| RTL co-simulation | Verilator models through Renode | Unsupported bus protocol reported | ELX-O-FW-1 | 5 |
| Hardware-in-the-loop | Plant FMUs or fixed-step C out; Evidence records in, pinned by `CheckId` | Variable-step constructs refused; evidence on an incompatible version does not count | ELX-O-FW-2 | 4 |
| Firmware flashing | `flash_device` plan with image digest, board serial and probe; read-back; target left in reset; hazards from the Network; Approval verified by the flashing client. Requires: AGT Firmware flashing | A read-back mismatch fails the Act and keeps the target in reset; an unverified Approval refuses the write | ELX-O-FW-3 | 3 |
| Bench sessions | `bench_session` plan contents for boards: person, serial, probe, lineage, count, expiry, hazards | A flash outside the lineage, over the count or after expiry ends the session and is refused | ELX-O-FW-3 | 3 |

## Batteries and power electronics

GP6's drone and GP12's battery sub-pack are energy products, so cells, packs, converters and magnetics need models that a pack engineer and a power designer trust. This section defines the cell-model ladder, pack design and the converter and magnetics libraries.

### Cell models

Cell models form a ladder, each rung with its validity envelope. Parameter sets are Materials (COV) whose fitting conditions become part of the envelope.

| Model | Equations | Valid for | Phase |
| --- | --- | --- | --- |
| Equivalent circuit | Open-circuit voltage OCV(SOC, T), R0 and RC pairs; LFP hysteresis by PyBaMM's one-state model [PyBaMM hysteresis], fitted to LFP charge and discharge data | Pack and BMS design in the fitted range | 4 (contract section 13.4) |
| SPMe | One particle per electrode plus electrolyte transport | Moderate rates | 4 (contract section 13.4) |
| DFN (P2D) | Porous-electrode theory over a particle-radius domain | High rates, plating risk | 5, FLX (contract section 13.4) |
| Swelling and stack pressure | Ai et al.'s swelling model as PyBaMM implements it [PyBaMM swelling]; cell thickness against state of charge with pad stiffness | Within the tested pressure range | 4 (contract section 13.4) |
| Degradation | SEI growth, plating, loss of active material | Within the tested conditions | 5 |
| Abuse mechanics | Wierzbicki and Sahraei's homogenized jellyroll [Wierzbicki and Sahraei 2013] with failure strain, coupled to runaway screening | Crush, penetration and crash screening | 6 (contract section 13.4) |

The hysteresis model counts only after its parameters are fitted to LFP data, and the abuse model enters phase 6 only once its calibration reproduces on the GP12 cell's crush tests.

**Decision D-ELX-19:** Equivalent-circuit cells are Network elements and SPMe cells are Flux forms, with PyBaMM as the reference for oracles and parameter sets.
*Why:* PyBaMM is BSD-3-Clause with SPM, SPMe and DFN models [PyBaMM], while native models give derivatives, Wasm portability and Flux thermal coupling.
*Rejected:* embedding PyBaMM, which puts a Python runtime in evaluation; DFN as an ordinary form, which needs nested domains.

DFN cells use Flux's parameter-domain forms ([FLX, Fields](03-flux.md#fields)), and pack-scale models embedding them follow in phase 6.

### Pack design

A pack is an Assembly of cell Instances, busbars, a battery management system (BMS) board and an enclosure, and ELX adds its electrical meaning:

- **Topology.** A `14s4p` arrangement generates the Network, each cell perturbed by its own parameters.
- **Busbars.** Flux DC conduction gives resistance and Joule heat; joint resistance is an element with stated uncertainty.
- **BMS.** A board designed here, running as models or as real firmware.
- **Thermal and swelling.** Cell heat goes to Flux conjugate heat transfer and the coolant loop's fluid elements; swelling sets pad compression and stack-force checks.
- **Safety.** Fuse coordination, isolation barriers and runaway propagation screening from published calorimetry.

### Power converters and magnetics

`std::electronics::power` provides buck, boost, flyback, forward, LLC, full-bridge, dual-active-bridge, PFC and inverter features returning Networks. Averaged models give part stresses that become `CatalogSelection` constraints, and the switched transient runs the closed loop. Losses become power Fields, and the hot loop's extracted subcircuit bounds switch-node overshoot.

| Quantity | `Interactive` method | `SignOff` method |
| --- | --- | --- |
| Core loss | iGSE with DC-bias correction; MagNet-trained models where available | Same, with flux waveforms from a Flux solve |
| Winding loss | Dowell (1966) [Dowell 1966]; Albach and Lammeraner for round wire, Albach and Ferreira for Litz [OpenMagnetics MKF] | 2D or 3D Flux eddy-current solve of the window |
| Inductance and leakage | Reluctance network with Roshen fringing and Zhang gap reluctance | Flux magnetostatic solve |
| Capacitance and thermal | Albach winding capacitance; thermal network | Flux electrostatic solve; conjugate heat transfer |

The MagNet Challenge 2023 benchmarked data-driven magnetics models and reported large gains in accuracy and size in 2025 [MagNet Challenge]; Crucible adopts its dataset and metric. OpenMagnetics MKF is MIT-licensed and a candidate for porting. A designed transformer gets an item number and a BOM like any Part.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Equivalent-circuit cells | OCV, resistance, RC pairs and an optional fitted one-state hysteresis as a Network element | Operation outside the parameter set's range is flagged with the variable | ELX-O-BAT-1 | 4 |
| SPMe cells | Forms with a parameter-set Material, to voltage, temperature and concentration Fields | Operation outside the parameter set's range is flagged with the variable | ELX-O-BAT-1 | 4 |
| Parameter fitting | Measured data to a set with confidence intervals | Unidentifiable parameters reported, never fixed silently | ELX-O-BAT-1 | 4 |
| Swelling and stack pressure | Ai et al.'s expansion and pad stiffness to pressure and force Fields | Outside the tested pressure range flagged | ELX-O-BAT-2 | 4 |
| Pack Network, busbars and thermal | Series-parallel layout with per-cell variation; Flux conduction and heat transfer | Inconsistent count or orientation is a compile error; limits fail checks | ELX-O-BAT-2 | 4 |
| Pack safety screening | Fuse coordination, barriers, runaway propagation | Results labelled as screening; missing calorimetry data listed | ELX-O-BAT-3 | 6 |
| Abuse mechanics and pack-scale DFN | Homogenized jellyroll failure model coupled to runaway screening; DFN cells in pack thermal | Outside the envelope the zone is `Invalid` and checks refuse | ELX-O-BAT-3 | 6 |
| Converter topologies and loops | Parameters to Networks with selection constraints; compensators with margins | An infeasible duty cycle is a typed error; an unstable loop fails with its margins | ELX-O-PWR-1 | 4 |
| Losses and parasitics | Loss Fields; hot-loop inductance from extracted subcircuits | Missing loss curves leave the check `Undecided` | ELX-O-PWR-1 | 4 |
| Magnetics design | Core, winding and gap to losses, inductances and Bodies | Saturation at peak current fails the check | ELX-O-PWR-2 | 4 |

## Wire harnesses

A harness joins boards, motors and sensors across the product, and its engineer's work spans three tabs, so this section walks one harness through all of them. ELX owns connectivity, wire tables and electrical checks; MEC owns 3D routes and formboard geometry; MFG owns the manufacturing package.

1. **Connectivity (ELX, phase 4).** A harness is a `Network` of connector, wire, splice and terminal catalog parts, joined to board ports by `connect` into one netlist. Connector selection uses the same catalog parts and mating facets as boards.
2. **Route (MEC, phase 3).** MEC routes bundles in 3D through the Assembly, with declared bundle diameters until ELX's wire tables exist ([MEC, Routing](06-mechanical.md#routing)).
3. **Lengths (ELX and MEC, phase 4).** Wire lengths are MEC's routed paths plus service loops and termination allowances; a missing route leaves a length `Undecided`, never zero.
4. **Checks (ELX, phase 4).** Gauge against current with bundle derating, voltage drop, pin ratings, terminal and seal compatibility, and shield termination.
5. **Package (MFG, phase 4).** MFG combines ELX's package data with MEC's 1:1 formboard into the harness manufacturing package.

The wire table holds, per variant, the ends, gauge, colour, cut and strip lengths, terminal and seal part numbers, and the terminal maker's crimp height and pull force. The package data adds connector face views from the mating side, splice and marker lists, a continuity and insulation test netlist, and the IPC/WHMA-A-620F workmanship class [IPC standards list].

VEC 2.2.0 is VDA 4968 and prostep ivip PSI21, and VEC 1.1.2 absorbed KBL 2.4 features [prostep VEC]. ECO's codec reads and writes VEC in phase 4, and reads KBL 2.5 SR-1, the current version [prostep KBL], in phase 5. Harness tools such as Zuken's E3.series cover cable plans, formboards and manufacturing outputs [Zuken E3.series]. Crucible adds one Network from board pin to harness terminal, checked by the same merge condition.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Harness connectivity | Harness Network joined to board ports | Pin mismatch is a compile error | ELX-O-HAR-1 | 4 |
| Wire table and lengths | Per-variant table from the Network and MEC routes. Requires: MEC Formboard geometry and lengths | A missing route makes the length `Undecided`, never 0 | ELX-O-HAR-1 | 4 |
| Gauge, drop and termination checks | Current from simulation or declared loads | Violation names the required gauge or terminal | ELX-O-HAR-1 | 4 |
| Harness package data | Face views, test netlist, terminal data and workmanship class for MFG's package | Missing terminal data listed | ELX-O-HAR-1 | 4 |
| VEC and KBL | VEC 2.2.0 read and write; KBL read | Unmapped elements listed | ELX-O-HAR-2 | 4 (VEC), 5 (KBL) |

## Robotics

Robot builders need their Assembly as a robot description that simulators and planners load, generated rather than hand-written so it never drifts from the design. Robots are Assemblies with MEC's joints and multibody dynamics; ELX attaches actuators, sensors and transmissions to joints, and inertial properties come from Bodies and Materials, never typed by hand.

The export formats are URDF, SDFormat, MJCF and USD (format details under [Reference](#robot-description-formats)). Collision geometry comes from `anvil::convex_decompose` with a stated Hausdorff bound, and exports carry their Change id. Crucible generates colcon-buildable packages for the newest LTS distribution that REP 2000 lists, now Jazzy Jalisco, supported until May 2029 [REP 2000]. Even-year releases are LTS, so Lyrical Luth, the May 2026 release [ROS 2 Kilted Kaiju], becomes the target once REP 2000 lists its platforms.

MuJoCo and Gazebo run as External Ops, and CI loads every export in both. A planning hook sends the model and collision Bodies to an external planner such as MoveIt. Trajectories return as `Field<(Instances, Time), Transform>`, along which torque, current and temperature are checked. Sending a robot program is the `send_robot_program` Act, and Crucible never starts motion (contract section 7.6).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kinematic chain view | Assembly with MEC joints to links, joints and attached models | A joint lacking limits or an actuator where an export needs one is reported | ELX-O-ROB-1 | 4 |
| URDF, SDFormat and MJCF export | Chain to files with stated mesh error | A cut closed loop is reported | ELX-O-ROB-1 | 4 |
| USD export | Chain to USD physics schemas | Unmapped elements listed | ELX-O-ROB-1 | 5 |
| ROS 2 description package | Chain to a colcon-buildable package for the current LTS distribution | A failed build is reported with its log | ELX-O-ROB-1 | 4 |
| Planning hooks | Model and collision world out, trajectory Field back | Planner failure returned as a typed error with its message | ELX-O-ROB-2 | 5 |
| Trajectory checks | Trajectory to torque, current and temperature checks | Exceedance fails with time and joint | ELX-O-ROB-2 | 4 |

## RF: antennas, arrays and matching networks

Radios put antennas inside enclosures, where the housing detunes them, so Crucible designs antennas as geometry in the product and analyses them in place. Antennas are Bodies: board copper, stamped metal, flex or coatings on the enclosure. `std::electronics::rf` provides patch, inverted-F, PIFA, monopole, dipole, loop, helix and slot features returning Bodies and ports, and board antennas are layout items under DRC.

Flux owns the solvers: frequency-domain Nédélec FEM for resonant antennas and FDTD for broadband problems ([FLX, Electromagnetics](03-flux.md#electromagnetics)). Antennas are analysed in their housing, a Material without frequency-dependent data is an error, and specific absorption rate is screening only.

**Arrays.** Phased arrays, frequency-selective surfaces and radomes are designed as one unit cell with periodic boundaries and Floquet ports. A finite array is then assembled from the cell, as in HFSS [PADT HFSS arrays]. FLX adds Bloch-periodic boundaries, Floquet ports and finite-array assembly in phase 5 (contract section 13.4). ELX adds `array(element, lattice, taper)`, which returns embedded element patterns as a `Field<(Ports, Direction, Frequency), Complex<Ratio>>` and array factors with scan loss, so GP11's CubeSat antennas stay in Crucible.

**Matching.** Matching synthesis builds L, Pi, T and multi-section networks, using real-frequency methods for broadband problems and reporting the Bode-Fano limit. Values snap to purchasable parts with vendor S-parameter models, Monte Carlo gives return-loss yield, and the result is a Proposal with a layout fragment. Linear RF analysis is phase 4; harmonic balance follows in phase 5.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Antenna features | Ingot features returning Bodies and ports | Geometry outside a feature's range is a typed error | ELX-O-RF-1 | 4 |
| Antenna analysis | Bodies, Materials and ports to `Field<(Ports, Frequency), Complex<Impedance>>`, far-field Fields and efficiency. Requires: FLX Frequency-domain electromagnetics | Under-resolved mesh or missing material data flagged with the fix | ELX-O-RF-1 | 4 |
| Antenna arrays | `array(element, lattice, taper)` to embedded patterns and array factors over scan angle | A lattice that admits grating lobes in the scan range is flagged with the angle | ELX-O-RF-3 | 5 |
| Matching synthesis | S-parameters and band to Network edits with yield | An infeasible match reports the Bode-Fano bound | ELX-O-RF-2 | 4 |
| Linear RF analysis | S-parameter network analysis | Non-passive data flagged | ELX-O-RF-2 | 4 |

## Requirements and system models

Requirements tie the whole product together, and their status should be computed from checks rather than kept by hand. This section defines `std::systems` records, requirement links and status, and SysML v2 and ReqIF exchange.

### SysML v2

OMG approved SysML v2.0, KerML 1.0 and the Systems Modeling API 1.0 on 21 July 2025 [OMG SysML v2 release], publishing SysML 2.0 in September 2025 [OMG SysML spec]. The release repository (EPL-2.0 libraries) was updated in March 2026 for ISO submission [SysML v2 release repository], and OMG's conformance suite is still in development.

**Decision D-ELX-20:** The system model is native Ingot in `std::systems`, and SysML v2 is an exchange format through its textual notation and the Systems Modeling API.
*Why:* one language keeps one model with three editors, and requirements reference real Parts, nets and checks with checked units.
*Rejected:* SysML v2 as a second authoring language, a second source of truth; SysML v1 XMI exchange, which loses semantics.

`std::systems` records mirror SysML v2 part and port definitions, connections, requirements, actions, states, constraints, allocations and variation, with a semantic mapping per concept. Crucible's own parser and serializer, an `io/` Wasm component, follow the published grammar with the pilot implementation as reference. Unmapped concepts survive as opaque annotations.

### Requirements and checks

```
use std::systems::{Requirement, Method, verify, satisfy, allocate}

pub const flight_time = Requirement {
    id: "SYS-012",
    text: "Hover endurance at sea level with nominal payload is at least 25 min.",
    endurance: 25min,
    methods: [Method.analysis, Method.test],
}
let hover = hover_endurance(drone, payload: 250g, air: isa(sea_level))
verify(flight_time, by: hover.require(hover.endurance >= flight_time.endurance, name: "hover_endurance"))
satisfy(flight_time, by: [drone.pack, drone.propulsion])
allocate(functions.power_distribution, to: drone.pdb_board)
```

- **Typed links.** `satisfy`, `verify`, `derive` and `allocate` point at Instances, checks, nets or requirements through `Query`s resolved every rebuild. A broken link is a `ResolveError`.
- **Computed status.** Status follows from `CheckOutcome`s: verified, failing, undecided, unverified, outside an envelope, or covered by a Waiver. Evidence records count only on the same design or a declared compatible one.
- **Computed impact.** A requirement edit re-evaluates only dependent checks, and a Proposal shows status changes beside geometry and metric diffs.
- **Exchange.** ReqIF passes through an `io/` Wasm component, keeping external ids; imported text arrives as `ExternalText`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `std::systems` modeling | Requirements, architecture, functions and allocations as Ingot records | Broken links are `ResolveError`s | ELX-O-SYS-1 | 3 |
| Computed requirement status | Status from check outcomes, Waivers and Evidence records | Evidence on an incompatible version excluded, with the reason | ELX-O-SYS-1 | 3 |
| SysML v2 exchange | Textual notation and API to and from `std::systems` | Unmapped concepts kept as annotations | ELX-O-SYS-2 | 4 |
| ReqIF exchange | Requirements with external ids | Unmapped attributes kept as annotations | ELX-O-SYS-2 | 4 |

## Reference

### Crates, packages and WIT

ELX owns no core crate (contract section 12). Its Rust ships in three places:

| Where | What ELX ships there |
| --- | --- |
| `flux-op-*` operation families, owned with FLX | `flux-op-mna` (operating point, sweeps, AC and noise, transient, switched transient, periodic steady state), `flux-op-macromodel` (vector fitting and passivity enforcement), `flux-op-control` (Riccati, realization, reduction) |
| std Wasm components under `std/` | DRC and fills on `anvil-planar`, the placer, the autorouter, `schematic.autodraw`, the schematic, layout and net-partition diff views, footprint generators, the Verilog-A front end, the SysML v2 and ReqIF codecs |
| `apps/` services | The flashing service in `apps/platform-*`; bench adapters for probes and serial ports |

Ingot packages: `std::electronics` (with `erc`, `rules`, `footprint`, `power`, `rf`, `compliance`) and `std::systems` (with `fluid` and the requirement records). The WIT package `crucible:electronics` holds the worlds of the placer, router, DRC and autodraw components; schematic and layout drawing goes through UIX's `crucible:ui/canvas2d`.

### ERC rule families

| Rule family | Examples | Source of truth |
| --- | --- | --- |
| Pin-type matrix | Two push-pull outputs on a net; input without a driver | Pin electrical types |
| Topology | Single-pin net; unconnected required pin; connected no-connect pin | `Network` |
| Net joins | Named nets joined without `tie` (unwaivable) | `Network`, net ties |
| Mated connectors | Mirrored or role-incompatible board-to-board pairs (`mated_pinout`) | Mating facets, Assembly placement |
| Voltage domains | Net range outside a pin's absolute maximum; logic-level mismatch | `Tol<Voltage>` on `Power` and pins |
| Power budget | Load current above a regulator's rating; inrush beyond a fuse | Catalog specifications |
| Bus semantics | I2C address collision; missing pull-ups; shared chip-selects | Compound port roles |
| Part rules | Missing required decoupling; floating strap pin | Catalog-part design rules |
| Protection | External connector without ESD protection | Ports marked `external` |
| Differential pairs | Polarity swapped across a hierarchy boundary | Net classes |

### Simulation engines

| Engine | Licence and note | Role |
| --- | --- | --- |
| ngspice | BSD-3-Clause core with LGPL-2 and GPL-2+ files [ngspice copyright] | Qualification reference and fallback (External Op) |
| VACASK | AGPL-3.0; 57.98 s on C6288 against ngspice's 71.81 s and Xyce's 151.57 s, authors' figures [VACASK] | Speed and accuracy cross-check |
| Xyce; OpenVAF | GPL-3.0 [Xyce] [OpenVAF]; OpenVAF emits native OSDI objects | Cross-check; not linked |
| Crucible engine | Apache-2.0 WITH LLVM-exception, Rust | Native and Verilog-A models, qualified vendor models, Monte Carlo, adjoints |

### Reliability handbooks

| Method | Edition | Use |
| --- | --- | --- |
| FIDES | Guide 2022 Edition A; registration required [FIDES] | Default for new designs |
| Telcordia SR-332 | Issue 4, March 2016 [PTC reliability models] | Telecom |
| MIL-HDBK-217F | Notice 2 [PTC reliability models] | Legacy and defence |
| IEC 61709 via SN 29500 | Reference conditions converted to operating ones [PTC reliability models] | Industrial |
| Physics of failure | Engelmaier and Coffin-Manson solder fatigue on Flux strain; Black's equation; Arrhenius wear-out | Critical joints and parts |

### Robot description formats

| Format | Contents | Notes |
| --- | --- | --- |
| URDF | Links, joints, inertials, meshes, transmissions, ros2_control tags | Tree only; closed loops are cut and the cut is reported |
| SDFormat | Worlds, models, sensors, closed loops | 1.12, the newest specification version [SDFormat spec] |
| MJCF | Bodies, joints, actuators, tendons, sensors, contact | MuJoCo is Apache-2.0 [MuJoCo]; sdformat_mjcf converts from SDFormat [SDFormat interoperability] |
| USD | Visual and physics schemas | Through an `io/` writer; gz-usd converts SDF |

### Typed failures

Every ELX failure renders as `elx/<snake_case>` (contract section 7.6), with a reason and fixes:

| Failure | Raised by | Typical fix |
| --- | --- | --- |
| `elx/named_net_join` | A pin placed in two named nets | Add a `tie` or remove one `connect` |
| `elx/net_merge` (`Conflict::NetMerge`) | A merge that unions nets distinct on both sides | Resolve the conflicting `connect`s on one branch |
| `elx/mated_pinout` | A mirrored or role-incompatible mated pair | Swap the connector variant or the placement side |
| `elx/drawn_short`, `elx/stale_annotation` | `schematic_matches_network` | Split the drawn group; remove the stale item |
| `elx/no_catalog_match` | A `CatalogSelection` with no candidate | Relax the tightest constraint named |
| `elx/selection_changes_land_pattern` | A post-release re-pick | Open a change order |
| `elx/unsupported_span` | A stackup span the fabricator cannot build | Use the nearest span named |
| `elx/step_too_small` | A transient that cannot advance | Check the device and nodes named |
| `elx/untranslated` | A Modelica construct outside the subset | Keep the FMU, or rewrite the construct |

## State of the art

Commercial tools are named as reference products, with no claim about their internals. Every figure is a target.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Connectivity capture | Drawn schematics with ERC [KiCad 10 release]; code capture with part picking [atopile]; AI-written design code [JITX] | Altium, KiCad 10, atopile, JITX, tscircuit, flux.ai | Code as source with a checked drawing and electrical review diffs | Net-merge conflicts 100% flagged; ERC recall 100%; GP5 board from requirements to DRC-clean Proposal with fewer human corrections than a recorded JITX or flux.ai session |
| Land patterns | Tolerance-driven IPC-7351B patterns [IPC-7351B release] | KiCad, over 78% generated | 100% generated for standard packages | 2,000 packages within ±1 µm of an independent calculation |
| Automatic placement | Analytical placement with net-crossing relaxation [Cypress paper] | Cypress [Cypress repository]; Allegro X AI; Quilter; JITX and flux.ai | Cypress plus height, thermal, decoupling and critical-net terms | Cypress's published results on its open suite |
| Interactive routing | Push and shove with walkaround and spring-back [KiCad PNS shove] | KiCad 10, Allegro, Xpedition | Same structure on exact geometry, delay-aware | Replayed sessions against the routing targets |
| Autorouting | Negotiated congestion [PathFinder award] with gridless detail; learned routers trail [PCBWorld] | Freerouting | Search-based Wasm router | PCBWorld-Bench: higher completion and fewer vias than Freerouting |
| DRC | Incremental, indexed, exact predicates | Altium, Allegro, KiCad | Tiled integer DRC on `anvil-planar` | 10 s full, 50 ms incremental; zero disagreements with a rational reference |
| Delay tuning | Time-domain constraints with per-layer profiles [KiCad 10 release] | KiCad 10, Allegro | Field-solved delay with tolerance propagation | TDR delay on GP5 coupons, ±2% |
| Cross-section RLGC | 2D quasi-static solution with roughness and causal dielectrics | Polar Si9000, HyperLynx | Flux 2D solve cached per cross-section | Conformal mapping and coupons, ±3% on Z0 |
| S-parameter macromodels | Vector fitting with passivity enforcement [Grivet-Talocia 2004] | SINTEF toolbox [SINTEF vector fitting] | Rust fitting, Hamiltonian check, residue perturbation | 100% passive; fit error at most the toolbox's |
| Channel simulation and compliance | Statistical eye and bit-by-bit with IBIS-AMI [IBIS 8.0]; standards-based compliance kits | Sigrity, HyperLynx [HyperLynx] | Both modes; AMI as External Ops; compliance packages per edition | IEEE 802.3ck contributed channels with its COM tool [IEEE 802.3ck tools]; eye height within 5% of a commercial tool |
| PDN impedance | Plane-pair cavity models with via coupling; full wave above their limit | Sigrity PowerSI, HyperLynx PI | FLX's plane-pair cavity model | Analytic resonances ±2%; VNA on GP5 ±15% |
| Parasitic extraction | Quasi-static RLCG with SPICE export [Ansys Q3D] | Ansys Q3D | FLX extraction plus ELX vector fitting to passive subcircuits | Analytic parallel-bar inductance; busbar against a published case |
| IR drop and board thermal | DC conduction with thermal coupling; layered board conduction | Sigrity PowerDC | Thin sheets, monolithic electro-thermal Newton; 2.5D layered thermal | Analytic ±1%; four-wire ±5%; GP5 thermocouples ±5 K |
| Antennas and arrays | Nédélec FEM with wave ports and fast sweep [Palace]; unit cells with Floquet ports and finite-array decomposition [PADT HFSS arrays] | Palace; openEMS [openEMS]; HFSS | Flux frequency-domain solver; `array` over FLX's periodic cells | Hallén dipole and cavity patch; resonance within ±1% of Palace; infinite dipole array reflection |
| Analog simulation | Modified nodal analysis, homotopy, block-triangular LU | VACASK [VACASK]; ngspice for compatibility [ngspice home]; LTspice | Rust engine with natively qualified vendor models | Vendor corpus 90% native-qualified; C6288 within 1.2× of VACASK |
| Switching converters | Ideal-switch piecewise-linear simulation [PLECS] | PLECS | `switched_transient` with cached topology matrices | 50× a device-level transient within the loss tables' tolerance |
| Compact models | Verilog-A compiled to OSDI [OpenVAF] | OpenVAF with ngspice or VACASK | Own front end to the kernel IR | BSIM4, PSP and VBIC curves, relative 10⁻⁶ |
| Reliability prediction | FIDES 2022 physics-informed models [FIDES] | Tools covering SR-332 and FIDES [PTC reliability models] | Four handbooks plus physics of failure | Worked examples to printed precision |
| Electric machines | Transient FEM with motion and loss models | Ansys, JMAG; Pyleecan with FEMM [Pyleecan] | Flux maps plus transient `SignOff` | TEAM problem 30a, induction motors [TEAM problems]; GP6 dynamometer, ±5 points |
| Magnetics core loss | Data-driven models [MagNet Challenge]; iGSE | OpenMagnetics MKF [OpenMagnetics MKF] | iGSE plus MagNet-trained models | MagNet metric no worse than the published winners |
| Battery cells | SPMe and DFN with SUNDIALS solvers | PyBaMM [PyBaMM] | Native ECM and SPMe; DFN through Flux | 1 mV RMS against PyBaMM on 1C discharge |
| Fluid systems | Stream-connector thermofluid libraries; real-fluid media | Amesim [Amesim domains]; Modelica.Fluid | `std::systems::fluid` with CoolProp media | Modelica.Fluid example agreement; analytic water-hammer wave speed |
| Modelica models | Object-oriented physical modeling with libraries [Dymola] | Dymola, OpenModelica | ECO's reader into Networks | 80% of MSL electrical, mechanical and thermal examples by phase 5 |
| Control design | Riccati, structured H∞, conic MPC | MATLAB Control System Toolbox [MathWorks Control] | Rust on `linalg`; MPC through Clarabel [Clarabel.rs] | Closed-form cases, relative 10⁻⁹; the 138-problem Maros-Meszaros QP set [Maros-Meszaros set] |
| Firmware-in-the-loop | Instruction-level emulation with peripheral models | Renode [Renode]; QEMU | Renode in lock-step | Identical traces in 100% of repeated runs |
| Harness data | VEC 2.2.0 [prostep VEC] | Zuken E3.series [Zuken E3.series], Capital | Harness Network with VEC exchange | Zero dropped elements in round trips |
| Robot descriptions | URDF, SDFormat and MJCF with converters [SDFormat interoperability] | Hand-written descriptions; CAD exporters | Generated from the Assembly | Mass properties to relative 10⁻⁹; clean loads in MuJoCo and Gazebo |
| System modeling | SysML v2 with KerML and the API [OMG SysML v2 release] | Pilot implementation [SysML v2 release repository] | Native `std::systems` | Pilot examples round trip; OMG suite when published |
| Matching networks | Real-frequency matching; Bode-Fano bound | Optenni Lab with vendor component libraries [Optenni Lab] | Synthesis with real parts and yield | Analytic L-networks to 10⁻⁶; bound never exceeded |

**Parity.** Each row names an incumbent's documented capability and where Crucible stands. The first three rows are the board workflow tiers that COV's parity map takes from this tab: each lands in the phase at which every capability it needs exists.

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Standing |
| --- | --- | --- | --- |
| Workflow tier: schematic and two-layer board | KiCad 10: schematic, ERC, push-and-shove routing, fabrication outputs [KiCad 10 release] | Drawn topology, ERC, Interactive routing, DRC, Board data for manufacturing; phase 3 | Equal at phase 3; ahead on merges, exact DRC and enclosure co-design |
| Workflow tier: multi-layer board with power and thermal | Altium Designer with its constraint manager [Altium constraint manager] and multi-board projects [Altium multi-board] | Constraint manager, Vias and HDI, IR drop, Board thermal, Mated board-to-board connectors; phases 3 and 4 | Equal by phase 4 (microvias and HDI arrive then); ahead on one Network across boards |
| Workflow tier: high-speed board | HyperLynx SI and PI with standards-based compliance for DDR and SerDes [HyperLynx] | Post-layout extraction, Pre-layout topology and channels, Interface compliance kits, Target impedance and PDN; phase 4 | Later: phase 4, after the phase 3 board tier |
| Code-first capture with AI | JITX: AI writes the code, generated pin assignment and routing [JITX]; tscircuit [tscircuit]; flux.ai [flux.ai] | Network builder, Automatic drawing, Automatic placement; phases 2 to 4 | Ahead: one repository with enclosure and firmware, error-budgeted checks, semantic merges, approvals over digests |
| Multi-board systems | Altium multi-board ERC detects net-to-pin and pin-to-pin wiring errors; assembly collision checks [Altium multi-board] | Mated board-to-board connectors; phase 3 | Ahead: no system schematic to synchronize |
| ECAD-MCAD co-design | Fusion raises cross-domain changes as alerts to synchronize [Fusion ECAD MCAD] | Enclosure co-design; phase 3 | Ahead: one Kiln graph, no sync step |
| Migration from Allegro and PADS | KiCad 10 imports Allegro boards (versions 16 to 23) and PADS designs [KiCad 10 importers] | Schematic import, Library migration through ECO; phase 3 | Equal: through KiCad 10 as an external tool |
| Vendor SPICE models on a laptop | ngspice runs PSpice and LTspice model parameters and netlists [ngspice home] | Vendor models; phase 3 | Equal at phase 3 for qualified models; ahead on error budgets |
| Ideal-switch converter simulation | PLECS: ideal switches, two steps per switching event, loss lookup tables [PLECS] | Switched transient; phase 4 | Equal at phase 4; ahead on error budgets and adjoints |
| RLCG extraction to SPICE | Q3D: frequency-dependent RLCG from busbars and inverter modules, equivalent SPICE models [Ansys Q3D] | Extracted parasitics as subcircuits; phase 4 | Equal at phase 4 |
| Antenna arrays | HFSS unit cells with paired periodic boundaries, Floquet ports and finite-array domain decomposition [PADT HFSS arrays] | Antenna arrays; phase 5 | Later: phase 5 with FLX's periodic cells |
| Modelica system models | Dymola: Modelica with libraries in many domains [Dymola] | Modelica translation coverage; FMU elements; phase 4 | Equal for the declared subset; FMU fallback for the rest |
| Hydraulic and thermofluid libraries | Amesim: hydraulic, pneumatic and thermal libraries with heat exchangers and refrigerant loops [Amesim domains] | Hydraulic and coolant elements (4); Two-phase and pneumatic elements (5) | Later: single-phase at phase 4, two-phase at phase 5 |
| Control design | MATLAB Control System Toolbox: PID autotuning, LQR and LQG, Kalman filters [MathWorks Control] | PID tuning; LQR, LQG and Kalman filters; phase 4 | Equal; ahead on unit-checked gains |
| Harness design | E3.series: cable plans, formboards and manufacturing outputs [Zuken E3.series] | Harness rows; phase 4 | Equal; ahead on one netlist from board to terminal |
| Concurrent board editing | flux.ai: real-time collaboration built in [flux.ai] | Data modules at scale, Net partition for merges; phase 3 | Ahead: row merges and live documents with connectivity conflicts detected |
| Integrated-circuit layout | Full-custom chip layout tools | None | Out of scope (contract section 13.1) |

## Platform notes

- **Integer board data.** Layout, DRC, fills and the board model hash identically on every Tier 1 platform, browsers included. Chord points come from `detmath`, and silkscreen text uses `anvil::text_outline` over registry font packages.
- **External Ops.** AMI models, native FMUs, emulators, Verilator, ngspice, vendor engines, robot simulators and firmware toolchains run on untrusted-evaluation workers, egress denied unless granted (contract section 7.8). Clients reach them remotely, and a desktop may run one locally as `Unverified` at `Interactive` at most; air-gapped installs need a local Linux worker for gate-quality results.
- **Vendor models offline.** Natively qualified vendor models run on every target, browsers included, with no External Op.
- **Emulator and simulator packages.** Renode 1.17.0 ships Linux x86-64 and ARM64, Apple-silicon macOS and Windows packages [Renode releases], so both server architectures run firmware. MuJoCo's prebuilt binaries cover Linux on x86-64 and AArch64, Windows on x86-64, and macOS [MuJoCo].
- **`f64` paths.** Analog analyses need `f64`, which Metal and WebGPU lack, so they run on CPU SIMD lanes everywhere. A server GPU class with Vulkan `SHADER_F64` may batch Monte Carlo at `Interactive`; CUDA and ROCm wait for the phase 4 gate decision of contract section 7.5.
- **Browser memory.** DRC, fills and analyses estimated above 512 MiB run in the disposable heavy worker ([PLT, Memory](12-platform-performance.md#memory)); larger boards go remote.
- **GPU placement.** The placer's FFT and gradient kernels go through `crucible:ops/flux` with CPU paths; placement is an edit, so class differences never reach an evaluation.
- **Hardware access.** Bench adapters and `flash_device` writes use USB and serial through `apps/platform-*`. Browsers flash only from the approval origin, using WebUSB, which MDN marks as limited availability [MDN WebUSB]. Web Serial has the same status [MDN Web Serial], and elsewhere a local adapter program connects to `api`.
- **Accessibility.** Schematics, netlists, rules and DRC results are AccessKit trees, so a screen-reader user can capture and review a whole design as code.

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| ING | Builder semantics for `network { … }`; `Schematic` and `Layout` table rows and the 10⁶-row layout fixture | `Network`, `Feature` | 2 |
| FLX | Port types and element libraries, the Verilog-A front end, board excitations, sheet and plane-pair geometry, vector fitting for extracted RLCG | `Network`, `Field` | 2 |
| ANV | Planar workloads with centre-radius arcs for `anvil-planar`; bend lines for `anvil::fold` | `Body` | 3 |
| KLN | Net partitions for the connectivity merge condition; `bare_board_invariant` and the covering-set policy; Software item definitions and `load` bindings; lifecycle placeholders; selections re-run with exclusions for the obsolescence check | `Network`, `Part` | 3 |
| MEC | Bare and assembled boards (flat and folded), connector `CoordSys` values, catalog mass and mating facets, harness connectivity and wire data, lumped motor and drive elements | `Part`, `Assembly`, `Network` | 2 |
| MFG | The board model with stackup, classes, footprints, test points, via protection and coating; the DRC engine for MFG's rule packs; harness package data; findings on board objects | `Part`, `Network` | 3 |
| COV | Equivalent-circuit, SPMe, swelling and abuse cell models; packs; fluid element libraries for envelopes; the board workflow tiers for the parity map | `Material`, `Field` | 4 |
| UIX | Canvas buffers for schematic, layout and constraint views; rule declarations; `schematic_matches_network`; the schematic, layout and net-partition diff nodes; recorded routing sessions | `crucible:ui/canvas2d` buffers | 3 |
| AGT | Std features with doc metadata; GP5 electronics checks; Proposals from placement, routing, autodraw, matching and decoupling tools; `flash_device` and `bench_session` plan contents with Network hazards | `CheckOutcome`, Proposal | 3 |
| ECO | The board, netlist and library models; the electrical semantics of IDX, IPC-2581, ODB++, IPC-D-356, KiCad, harness, robot and systems formats; the element libraries the Modelica reader targets; `CatalogSelection` | `Network`, `Part` | 3 |
| PLT | The flashing service and bench adapters in `apps/platform-*` | Approval-verified transfers | 3 |

## Oracles

ELX oracles live in `oracles/elx/`; held-out sets are never shown to agents, and loosening a tolerance needs human approval.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ELX-O-EXT-1 | Port types, element libraries and analyses defined in a user namespace | Compile and evaluate identically to their std equivalents |
| ELX-O-NET-1 | Network builder and hierarchy | Connect order never changes the net partition; hierarchical golden designs flatten to known netlists |
| ELX-O-NET-2 | Net ties, connectivity merges and mated connectors | Every seeded net-merging branch pair reported as `Conflict::NetMerge`; non-overlapping pairs merge clean; every untied named-net join fails; every seeded mirrored or role-incompatible mezzanine pair fails `mated_pinout` and correct pairs pass |
| ELX-O-NET-3 | Port types and element stamps | Every std port's power expression type-checks and seeded wrong ones fail; RLC, motor and drivetrain cases match analytic solutions |
| ELX-O-VAR-1 | Variant covering set and bare board | Every listed sellable configuration and the pairwise covering set build; a seeded footprint-changing variant fails `bare_board_invariant` |
| ELX-O-SCH-1 | Drawn schematics and automatic drawing | In 10⁵ random view and code edits, view edits never change connectivity and no drawn group spans two nets after any code edit; after `schematic.autodraw`, `schematic_matches_network` passes and the rows are identical across runs |
| ELX-O-SCH-2 | ERC | 100% recall on 300 human-labelled seeded schematics and a held-out 100; zero false positives on clean designs; an unsigned `#[waive]` never passes |
| ELX-O-SCH-3 | Netlists, schematic import and migration | Re-import equality; migrated designs' netlists equal the source tool's own netlist export |
| ELX-O-SCH-4 | Drawing output | Visual regression against stored references; placeholders filled only at output |
| ELX-O-SCH-5 | Data modules at scale | The 10⁶-row layout fixture parses and hashes in under 1 s natively (target); a region split rebuilds identically |
| ELX-O-SCH-6 | Electronics review diffs | Every seeded change (moved symbol, pin moved to another net, value change, copper added on one layer, rule change) appears exactly once in the right view; unchanged items never appear |
| ELX-O-CAT-1 | Facets, symbols and consistency checks | Every seeded inconsistent record blocked with the right `CatalogError` |
| ELX-O-CAT-2 | Footprint generators | Pad geometry within ±1 µm of an independent calculation on 2,000 packages |
| ELX-O-CAT-3 | Selections and offers | Identical pins give identical parts everywhere; argument changes re-resolve before release; update diffs list every substitution; a post-release offer refresh leaves the assembly BOM unchanged; a re-run with an excluded part returns the next candidates |
| ELX-O-CAT-4 | Parts policy | A non-approved part fails the policy check unless a Waiver names it; a new-part Proposal creates all its records |
| ELX-O-CAT-5 | Datasheet extraction | Agreement with hand-entered held-out records; every value cites a page |
| ELX-O-BRD-1 | Stackups, classes, layout geometry and board Bodies | Fabricator capability replay; concentric arc offsets exact; rasterized copper equals layout data within the chord bound |
| ELX-O-BRD-2 | Enclosure co-design | Scripted GP5 enclosure changes update placements or fail with `ResolveError` |
| ELX-O-BRD-3 | IDX exchange | IDX baselines and scripted change scenarios; proposals conflicting with locks rejected item by item |
| ELX-O-BRD-4 | Folding and flex strain | Folded geometry equals analytic cylinder maps; strain matches thin-beam bending and a 3D FEM cross-check |
| ELX-O-BRD-5 | Lifecycle placeholders | Assigning a revision or an engine upgrade with bit-level changes only flips zero boards to modified |
| ELX-O-LAY-1 | DRC and vias | Seeded violations all found against a slow exact-rational checker; rotated, mirrored and translated boards give identical violation sets; via-in-pad without a filled and capped type fails |
| ELX-O-LAY-2 | Fills and teardrops | Idempotent and tile-order independent; every derived fill passes the exact checker with zero tolerance |
| ELX-O-LAY-3 | Interactive placement and routing | Recorded sessions replay byte for byte; DRC clean after every finished route; 16 ms per update with 50 shoved items (target); overridden results never reach the shared cache |
| ELX-O-LAY-4 | Autorouting | PCBWorld-Bench metrics against Freerouting; no Proposal with DRC errors |
| ELX-O-LAY-5 | Automatic placement | Cypress open suite and held-out boards; targets in State of the art |
| ELX-O-LAY-6 | Rules, functional spacing and isolation barriers | Precedence property tests; IPC-2221 spacing reproduced per category and voltage; worked examples from each supported safety standard reproduced |
| ELX-O-LAY-7 | Test points and coating | Coverage recomputed from the netlist; every net without access receives a proposed test point or a stated reason; coated probe sites fail access |
| ELX-O-SI-1 | Impedance, RLGC, extraction and delay | ±1% against conformal-mapping solutions; ±10% against measured GP5 coupons (target) |
| ELX-O-SI-2 | Macromodels | Fit error under the stated bound; passive after enforcement by an independent Hamiltonian check |
| ELX-O-SI-3 | IBIS and channels | IBISCHK8 parse agreement; vendor AMI examples reproduced; a forged receipt or two differing runs never pass a `SignOff` check |
| ELX-O-SI-4 | Interface compliance kits | Published compliance examples for each supported DDR, PCIe and USB edition reproduced; IEEE 802.3ck contributed channels give the COM tool's verdicts |
| ELX-O-PI-1 | PDN, decoupling and IR drop | Analytic cavity resonances ±2%; analytic strip and annulus resistances ±1%; exact optimum on small decoupling instances |
| ELX-O-PI-2 | Electro-thermal coupling | Analytic self-heating of a uniform strip; `Runaway` reported at the turning point under current drive |
| ELX-O-EMC-1 | EMC screening | Analytic small-loop and short-dipole radiation; seeded rule and coupling cases; GP6 chamber scans as screening references |
| ELX-O-TH-1 | Board thermal | Layered model within its stated bound of explicit 3D copper on zoom cases; GP5 thermocouples ±5 K (target) |
| ELX-O-SIM-1 | Analog analyses and their error budgets | ngspice regression corpus run as an External Op and textbook circuits, relative 10⁻³ or absolute 1 µV; an LC oscillator's transient reports `Indicator` temporal error without the adjoint or step-halving estimate; on held-out circuits the `mna_newton` class shows zero undershoots in at least 300 cases, and results outside its envelope report `Indicator` |
| ELX-O-SIM-2 | Vendor models | At least 90% of the unencrypted vendor corpus native-qualified at the phase 3 gate (target); every qualified model matches the ngspice External Op within its bench tolerance on held-out benches |
| ELX-O-SIM-3 | Verilog-A compact models | I-V and C-V curves against OpenVAF-compiled references run as External Ops, relative 10⁻⁶ |
| ELX-O-SIM-4 | Monte Carlo, sensitivity and worst case | Identical samples in every class and under re-randomized names; added samples leave earlier ones unchanged; adjoint sensitivities pass Taylor tests |
| ELX-O-SIM-5 | Mixed-signal | Event times within one analog step of ngspice XSPICE references |
| ELX-O-SIM-6 | Switched transient | Buck and three-phase inverter waveforms agree with device-level transients within the loss tables' tolerance; event times exact to the step tolerance; speed-up of at least 50× (target) |
| ELX-O-REL-1 | Reliability and derating | Handbook worked examples to printed precision; physics-of-failure models against their cited datasets |
| ELX-O-MCH-1 | Machines | Analytic slotless fields and winding factors, torque ±3%; TEAM problem 30a; GP6 dynamometer efficiency ±5 points (target) |
| ELX-O-MCH-2 | Actuators, sensors, drives and propeller loads | Analytic solenoid force; datasheet transfer curves; averaged-model cases against ngspice; propeller torque from a map equals the map's source values at its nodes |
| ELX-O-CTL-1 | Control design and code generation | Closed-form Riccati, margin and reduction-bound cases to relative 10⁻⁹; Maros-Meszaros QPs to their reference objectives; generated code bit-exact with the Ingot reference |
| ELX-O-CTL-2 | FMU elements and bus simulation | Reference FMUs map ports and units correctly; the FMI-LS-BUS demo FMUs for CAN and FlexRay exchange their frames |
| ELX-O-CTL-3 | Modelica translation coverage | The share of MSL `Modelica.Electrical`, `Mechanics.Rotational`, `Mechanics.Translational` and `Thermal.HeatTransfer` examples that translate and match MSL reference results within their tolerances, reported per release; 80% by phase 5 (target) |
| ELX-O-FLD-1 | Fluid element libraries | Modelica.Fluid example agreement; analytic water-hammer wave speed; CoolProp property values reproduced at sampled states |
| ELX-O-FW-1 | Firmware-in-the-loop | Reference firmware traces identical across repeated runs per class and per Renode release, on x86-64 and ARM64 workers; PWM-to-RC timing error within the reported bound |
| ELX-O-FW-2 | Hardware-in-the-loop | Fixed-step exports bit-exact with the reference; evidence on an incompatible version never counts; two Evaluations of one Change read the same pinned Evidence records |
| ELX-O-FW-3 | Firmware flashing and bench sessions | Every client path flashes only after verifying the Approval; a flashing attempt from the main web origin fails; targets stay in reset until released at the bench; a read-back mismatch fails the Act; rotational ports add the propellers step; a bench session refuses flashes beyond its count, after its expiry or outside its lineage |
| ELX-O-BAT-1 | Cell models | 1 mV RMS against PyBaMM on shared parameter sets (target); analytic diffusion; fitted parameters recover known values; fitted LFP hysteresis reproduces measured loops |
| ELX-O-BAT-2 | Packs and swelling | Hand-computed pack resistance and capacity; analytic busbar resistance; swelling against PyBaMM's swelling model; GP6 pack voltage under 30 mV RMS per cell (target) |
| ELX-O-BAT-3 | Pack safety and abuse | Published coordination examples; abuse screening against the jellyroll model's calibration data and GP12 crush tests |
| ELX-O-PWR-1 | Converters and extracted parasitics | Textbook steady-state and averaged-model cases; analytic loop inductance; fitted subcircuits passive and within the fit bound of `flux::extract_rlcg` on parallel bars; GP6 calorimetric efficiency |
| ELX-O-PWR-2 | Magnetics | MagNet metric no worse than the iGSE baseline; Dowell analytic cases |
| ELX-O-HAR-1 | Harness | Hand-checked golden harness wire table, lengths and checks; package contents complete |
| ELX-O-HAR-2 | VEC and KBL | Schema validation and round trip with zero dropped elements |
| ELX-O-ROB-1 | Robot exports | Mass properties equal Anvil's to relative 10⁻⁹; files load in MuJoCo and Gazebo without warnings; sdformat_mjcf round trip |
| ELX-O-ROB-2 | Trajectories and planning hooks | Analytic single-joint cases; recorded planner sessions |
| ELX-O-RF-1 | Antennas | Dipole impedance against Hallén's integral equation for the modelled radius; cavity-model patch; Palace cross-check, ±2% resonance |
| ELX-O-RF-2 | Matching and linear RF | Analytic L-networks to 10⁻⁶; Bode-Fano bound never exceeded; textbook amplifier cases |
| ELX-O-RF-3 | Antenna arrays | Array factors of uniform and tapered linear arrays against closed forms; grating-lobe onset at the analytic scan angle; an infinite dipole array's active reflection against a published reference |
| ELX-O-SYS-1 | System model and status | Resolution tests; seeded status corpus |
| ELX-O-SYS-2 | SysML v2 and ReqIF | Round trip of the pilot implementation's examples and sample ReqIF files with no dropped elements |
| ELX-O-SYS-3 | Software items | Seeded board-description mismatches all fail; reference firmware rebuilds to identical hashes; a binary swap after approval voids the Approval |
| ELX-O-DET-1 | Determinism and label invariance | Golden boards hash identically on every Tier 1 platform; re-randomized names and designators leave copper and check values identical |

## Phasing

Shared capabilities take their phase from contract section 13.4: conjugate heat transfer, Helmholtz solvers, electro-thermal coupling, RLCG and full-wave extraction, FMU export and SSP, and every battery cell row. ELX's parity-floor rows land no later than 13.4 allows. Native vendor dialects and mated connectors arrive in phase 3; hydraulic and coolant libraries, the switched transient and compliance kits in phase 4; two-phase and pneumatic libraries in phase 5. No ELX row precedes a row it requires.

| Phase | ELX contribution to the gate |
| --- | --- |
| 0 | None |
| 1 | No gate contribution. The circuit-simulation research track prototypes the modified-nodal-analysis engine, assembles the vendor-model corpus and measures the Verilog-A front end's scope |
| 2 | GP3: the `network { … }` builder, rotational, translational and thermal ports, drivetrain elements and `CatalogSelection` over pinned definitions. ECO's IDF, STEP board and IDX baseline import serve enclosure design; ING measures the 10⁶-row layout fixture |
| 3 | GP5, its board fabricated and assembled from Crucible outputs alone, through the phase 3 rows above. Evidence: DRC and ERC clean; the fabricator's manufacturability review with zero errors; coupon impedance within ±10% and hottest part within ±5 K of measurement (targets); board data identical on every Tier 1 platform; 90% of the vendor corpus native-qualified (target) |
| 4 | GP6, through the phase 4 rows above. Evidence (targets): hover endurance ±10% of flight test; motor efficiency ±5 points; pack voltage under 30 mV RMS per cell; attitude-loop overshoot and settling ±20%; antenna resonance ±2% |
| 5 | GP7: the MEMS reduced-order model as a Network element for readout simulation. The other phase 5 rows serve no gate |
| 6 | GP11 CubeSat: board, harness and firmware flows. GP12 battery sub-pack with BMS, harness and charger: pack safety, abuse mechanics, pack-scale DFN, high-voltage barriers, coolant loop |
| 7 | None |

## Open questions

1. **Verilog-A front end scope.** The phase 1 research track's prototype measures whether a clean-room front end covers BSIM4, PSP and VBIC in phase 3. Until that measurement exists, the fallback stands: ported SPICE3 models plus natively qualified vendor models, with ngspice for the rest.

## Contract change requests

None.

## Sources

Vendor performance claims are reported as the vendors state them.

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [KiCad 10 release] | KiCad project, "Version 10.0.0 Released", 20 March 2026 | https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/ | October 2026 |
| [KiCad 10 importers] | KiCad project, "Three New Importers in KiCad 10: Allegro, PADS and gEDA" | https://www.kicad.org/blog/2026/02/Three-New-Importers-in-KiCad-10-Allegro-PADS-and-gEDA/ | 12 October 2026 |
| [OMG SysML v2 release] | Object Management Group, press release on SysML v2.0, KerML 1.0 and Systems Modeling API and Services 1.0, 21 July 2025 | https://www.omg.org/news/releases/pr2025/07-21-25.htm | October 2026 |
| [OMG SysML spec] | Object Management Group, SysML specification page | https://www.omg.org/spec/SysML | October 2026 |
| [atopile] | atopile repository (MIT) | https://github.com/atopile/atopile | October 2026 |
| [JITX] | JITX home page | https://www.jitx.com/ | 12 October 2026 |
| [tscircuit] | tscircuit repository (MIT) | https://github.com/tscircuit/tscircuit | 12 October 2026 |
| [flux.ai] | Flux home page | https://www.flux.ai/ | 12 October 2026 |
| [Cypress paper] | Cypress: VLSI-inspired PCB placement with GPU acceleration, ISPD 2025 | https://www.csl.cornell.edu/~zhiruz/pdfs/cypress-ispd2025.pdf | October 2026 |
| [Cypress repository] | NVlabs Cypress repository (Apache-2.0) | https://github.com/NVlabs/Cypress | October 2026 |
| [ngspice home] | ngspice project home page | https://ngspice.sourceforge.io/ | October 2026 |
| [ngspice copyright] | Debian copyright file for ngspice 47 | https://tracker.debian.org/media/packages/n/ngspice/copyright-47ds-1 | October 2026 |
| [ngspice news] | ngspice project, news and release history | https://ngspice.sourceforge.io/news.html | October 2026 |
| [VACASK] | VACASK repository (AGPL-3.0) with benchmark tables | https://codeberg.org/arpadbuermen/VACASK | October 2026 |
| [OpenVAF] | OpenVAF repository (GPL-3.0) | https://github.com/pascalkuthe/OpenVAF | October 2026 |
| [Xyce] | Xyce repository (GPL-3.0) | https://github.com/Xyce/Xyce | October 2026 |
| [SSP home] | SSP standard home page | https://ssp-standard.org/ | October 2026 |
| [FMI 3.0.2 release] | FMI project, "FMI 2.0.5 and FMI 3.0.2 released" | https://fmi-standard.org/news/2024-11-27-fmi-2.0.5-and-3.0.2 | October 2026 |
| [SSP 2.0 release] | SSP project, "SSP 2.0 release" | https://ssp-standard.org/news/2024-12-20-ssp-2-0-release/ | October 2026 |
| [FMI-LS-BUS 1.0] | FMI project, "Release of FMI-LS-BUS v1.0" | https://fmi-standard.org/news/2025-07-21-fmi-ls-bus-v1.0-release/ | October 2026 |
| [FMI news] | FMI project, news listing for 2025 and 2026 | https://fmi-standard.org/news/ | October 2026 |
| [FMI-LS-BUS examples] | Modelica Association, FMI-LS-BUS examples repository (demo FMUs for CAN and FlexRay) | https://github.com/modelica/fmi-ls-bus-examples | October 2026 |
| [prostep IDX forum] | prostep ivip, ECAD/MCAD Collaboration Implementor Forum | https://www.prostep.org/en/projects/ecad/mcad-collaboration-implementor-forum | October 2026 |
| [Ucamco Gerber downloads] | Ucamco, Gerber format downloads (Layer Format revision 2026.05, Job Format 2020.08, XNC 2021.11) | https://www.ucamco.com/en/gerber/downloads | October 2026 |
| [Gerber X3 release] | I-Connect007, "Ucamco releases final version of the Gerber X3 specification", 2020 | https://iconnect007.com/index.php/article/122204/ucamco-releases-final-version-of-the-gerber-x3-specification/122207?skin=pcb | October 2026 |
| [Wikipedia Gerber] | Wikipedia, "Gerber format" | https://en.wikipedia.org/wiki/Gerber_format | October 2026 |
| [Siemens ODB++] | Siemens, ODB++ product page | https://www.siemens.com/en-us/products/pcb/odb-plus-plus/ | October 2026 |
| [IPC-2581C release] | IPC, "IPC releases IPC-2581 Revision C", 1 December 2020 | https://www.electronics.org/news-release/ipc-releases-ipc-2581-revision-c-generic-requirements-printed-board-assembly-products | October 2026 |
| [IPC-2581 Consortium] | IPC-2581 Consortium home page | https://www.ipc2581.com/ | October 2026 |
| [IBIS home] | IBIS Open Forum home page (IBIS 8.0, Touchstone 2.1, IBIS-ISS 1.0) | https://ibis.org/ | October 2026 |
| [IBIS 8.0] | IBIS Open Forum, IBIS 8.0 page (ratified 5 December 2025) | https://ibis.org/ver8.0/ | October 2026 |
| [prostep VEC] | prostep ivip ECAD wiki, VEC specifications | https://ecad-wiki.prostep.org/specifications/vec/ | October 2026 |
| [prostep KBL] | prostep ivip ECAD wiki, KBL specifications (KBL 2.5 SR-1) | https://ecad-wiki.prostep.org/specifications/kbl/ | October 2026 |
| [ROS 2 Kilted Kaiju] | Open Robotics, "ROS 2 Kilted Kaiju Released", 23 May 2025 | https://www.openrobotics.org/blog/2025/5/23/ros-2-kilted-kaiju-released | October 2026 |
| [REP 2000] | ROS REP 2000, "ROS 2 Releases and Target Platforms" | https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-2000.rst | October 2026 |
| [MuJoCo] | MuJoCo repository (Apache-2.0) | https://github.com/google-deepmind/mujoco | October 2026 |
| [SDFormat interoperability] | SDFormat, "Interoperability with other modeling formats" | https://sdformat.org/tutorials/developers/interoperability_formats/ | October 2026 |
| [SDFormat spec] | SDFormat specification page (versions 1.4 to 1.12) | http://sdformat.org/spec | October 2026 |
| [Renode] | Renode repository (MIT) | https://github.com/renode/renode | October 2026 |
| [Renode releases] | Renode releases page (1.17.0 packages, including `linux-arm64-portable`) | https://github.com/renode/renode/releases | 12 October 2026 |
| [Renode RTL co-simulation] | RISC-V International blog, "CPU RTL co-simulation in Renode" | https://riscv.org/blog/cpu-rtl-co-simulation-in-renode/ | October 2026 |
| [Renode peripherals] | Renode documentation, "Writing peripherals" (SystemRDL stubs through peakrdl-renode; SVD register tags) | https://renode.readthedocs.io/en/latest/advanced/writing-peripherals.html | October 2026 |
| [Verilator] | Verilator repository (LGPL-3.0 or Artistic-2.0) | https://github.com/verilator/verilator | October 2026 |
| [PCBWorld] | PCBWorld: a benchmark environment for engine-grounded PCB design automation, arXiv 2607.05915 | https://arxiv.org/abs/2607.05915 | October 2026 |
| [SysML v2 release repository] | OMG Systems Modeling community, SysML v2 release repository | https://github.com/systems-modeling/sysml-v2-release | October 2026 |
| [openEMS] | openEMS documentation, introduction | https://docs.openems.de/intro.html | October 2026 |
| [Palace] | Palace repository (Apache-2.0) | https://github.com/awslabs/palace | October 2026 |
| [PADT HFSS arrays] | PADT, "Efficient and accurate simulation of antenna arrays in HFSS" | https://www.padtinc.com/blog/efficient-and-accurate-simulation-of-antenna-arrays-in-hfss/ | 12 October 2026 |
| [Freerouting] | Freerouting repository (GPL-3.0) | https://github.com/freerouting/freerouting | October 2026 |
| [MagNet Challenge] | Chen, Sullivan et al., "MagNet Challenge for Data-Driven Power Magnetics Modeling", IEEE Open Journal of Power Electronics 6 (2025), record page | https://collaborate.princeton.edu/en/publications/magnet-challenge-for-data-driven-power-magnetics-modeling/ | October 2026 |
| [Allegro X AI] | Cadence, "Cadence Introduces Allegro X AI", Business Wire, 6 April 2023 | https://www.businesswire.com/news/home/20230406005098/en/Cadence-Introduces-Allegro-X-AI-Accelerating-PCB-Design-with-More-Than-10X-Reduction-in-Turnaround-Time | October 2026 |
| [Quilter] | Quilter, "About" | https://www.quilter.ai/about | October 2026 |
| [PyBaMM] | PyBaMM repository (BSD-3-Clause) | https://github.com/pybamm-team/PyBaMM | October 2026 |
| [PyBaMM API] | PyBaMM documentation, public API | https://docs.pybamm.org/en/stable/source/user_guide/fundamentals/public_api.html | October 2026 |
| [PyBaMM hysteresis] | PyBaMM documentation, `OneStateHysteresisOpenCircuitPotential` (after Börjesson Axén et al., Journal of Energy Storage 48, 2022) | https://docs.pybamm.org/en/latest/source/api/models/submodels/interface/open_circuit_potential/one_state_hysteresis_ocp.html | October 2026 |
| [PyBaMM swelling] | PyBaMM documentation, `SwellingOnly` (after Ai, Kraft, Sturm, Jossen and Wu, J. Electrochem. Soc. 167(1) 013512) | https://docs.pybamm.org/en/latest/source/api/models/submodels/particle_mechanics/swelling_only.html | October 2026 |
| [Wierzbicki and Sahraei 2013] | Crossref record: Wierzbicki and Sahraei, "Homogenized mechanical properties for the jellyroll of cylindrical Lithium-ion cells", Journal of Power Sources 241 (2013) 467–476 | https://api.crossref.org/works/10.1016/j.jpowsour.2013.04.135 | October 2026 |
| [Pyleecan] | Pyleecan repository (Apache-2.0) | https://github.com/Eomys/pyleecan | October 2026 |
| [KiCad PNS shove] | KiCad source documentation, `PNS::SHOVE` class reference | https://docs.kicad.org/doxygen/classPNS_1_1SHOVE.html | October 2026 |
| [iOverlay] | iOverlay repository (MIT or Apache-2.0) | https://github.com/iShape-Rust/iOverlay | 12 October 2026 |
| [Clipper2] | Clipper2 repository (BSL-1.0) | https://github.com/AngusJohnson/Clipper2 | October 2026 |
| [faer sparse] | faer documentation, sparse linear algebra module (MIT) | https://docs.rs/faer/latest/faer/sparse/linalg/index.html | October 2026 |
| [Clarabel.rs] | Clarabel.rs repository (Apache-2.0) | https://github.com/oxfordcontrol/Clarabel.rs | October 2026 |
| [Rumoca] | Rumoca repository (Apache-2.0) | https://github.com/CogniPilot/rumoca | October 2026 |
| [ModelingToolkit] | ModelingToolkit.jl repository | https://github.com/SciML/ModelingToolkit.jl | October 2026 |
| [Modelica Standard Library] | Modelica Standard Library repository (BSD-3-Clause, v4.1.0) | https://github.com/modelica/ModelicaStandardLibrary | October 2026 |
| [OSMC-PL 1.8] | Open Source Modelica Consortium, OSMC Public License 1.8 | https://openmodelica.org/osmc-pl/osmc-pl-1.8.txt | October 2026 |
| [Dymola] | Dassault Systèmes, Dymola product page | https://www.3ds.com/products/catia/dymola | 12 October 2026 |
| [Amesim domains] | Siemens Simcenter blog, "Many physical domains and applications in one system simulation tool" | https://blogs.sw.siemens.com/simcenter/many-physical-domains-and-applications-in-one-system-simulation-tool/ | 12 October 2026 |
| [CoolProp] | CoolProp repository (MIT) | https://github.com/CoolProp/CoolProp | 12 October 2026 |
| [PLECS] | Plexim, PLECS product page | https://www.plexim.com/products/plecs | 12 October 2026 |
| [Ansys Q3D] | Ansys, Q3D Extractor product page | https://ansys.synopsys.com/products/electronics/ansys-q3d-extractor | 12 October 2026 |
| [HyperLynx] | Siemens, HyperLynx product page | https://www.siemens.com/en-us/products/pcb/hyperlynx/ | 12 October 2026 |
| [MathWorks Control] | MathWorks, Control System Toolbox product page | https://www.mathworks.com/products/control.html | 12 October 2026 |
| [Zuken E3.series] | Zuken, E3.series product page | https://www.zuken.com/en/product/e3series/ | 12 October 2026 |
| [Altium multi-board] | Altium, "Multi-board design" documentation | https://altium.com/documentation/altium-designer/multi-board-design | 12 October 2026 |
| [SINTEF vector fitting] | SINTEF, Vector Fitting software page | https://www.sintef.no/en/software/vector-fitting/ | October 2026 |
| [OpenMagnetics MKF] | OpenMagnetics MKF repository (MIT) | https://github.com/OpenMagnetics/MKF | October 2026 |
| [Altium constraint manager] | Altium, "Defining Design Requirements Using the Constraint Manager" | https://altium.com/jp/documentation/node/322309/printable/print | October 2026 |
| [IPC-7351B release] | Electronic Specifier, "IPC releases new revision of surface mount design and land pattern standard", 23 July 2010 | https://www.electronicspecifier.com/?p=119981 | October 2026 |
| [GlobalSpec IPC-7351] | GlobalSpec standards record for IPC-7351 | https://standards.globalspec.com/std/1267508/ipc-7351 | October 2026 |
| [Fusion ECAD MCAD] | Autodesk Fusion blog, "Why ECAD MCAD Integration Just Makes Sense", 3 July 2025 | https://www.autodesk.com/products/fusion-360/blog/why-ecad-mcad-makes-sense/ | October 2026 |
| [PTC reliability models] | PTC Windchill Risk and Reliability reference guide, prediction model descriptions | https://support.ptc.com/help/wrr/r12.0.4.0/en/wrr/ReferenceGuide/prediction/model_descriptions.html | October 2026 |
| [FIDES] | FIDES reliability methodology home page | https://www.fides-reliability.org/en | October 2026 |
| [KiCad IPC API] | KiCad developer documentation, IPC API | https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/ | October 2026 |
| [KiCad 9 release] | KiCad project, "Version 9.0.0 Released", 20 February 2025 | https://www.kicad.org/blog/2025/02/Version-9.0.0-Released/ | October 2026 |
| [KiCad 9 project manager] | KiCad 9.0 documentation, KiCad project manager (importing non-KiCad projects) | https://docs.kicad.org/9.0/en/kicad/kicad.html | October 2026 |
| [KiCad 9 PCB editor] | KiCad 9.0 documentation, PCB Editor (fabrication and 3D model exports) | https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html | October 2026 |
| [KiCad library licence] | KiCad, library licence (CC-BY-SA 4.0 with a design exception) | https://www.kicad.org/libraries/license/ | October 2026 |
| [ECSS derating] | ECSS, ECSS-Q-ST-30-11C Rev.2, "Derating – EEE components", 23 June 2021 | https://ecss.nl/standard/ecss-q-st-30-11c-rev-2-derating-eee-components-23-june-2021/ | October 2026 |
| [MDN WebUSB] | MDN Web Docs, WebUSB API | https://developer.mozilla.org/en-US/docs/Web/API/WebUSB_API | October 2026 |
| [MDN Web Serial] | MDN Web Docs, Web Serial API | https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API | October 2026 |
| [TEAM problems] | International Compumag Society, TEAM problems | https://www.compumag.org/wp/team/ | October 2026 |
| [SPDX specifications] | SPDX, specifications page (SPDX 3.0; ISO/IEC 5962:2021) | https://spdx.dev/use/specifications/ | October 2026 |
| [CycloneDX] | CycloneDX, specification overview (1.7, 21 October 2025; ECMA-424) | https://cyclonedx.org/specification/overview/ | October 2026 |
| [NISTIR 7648] | NIST, NISTIR 7648, "Representation of a Thermal Resistor Network Model of a Packaged Component in STEP AP210 Edition 2" (JESD15-3 two-resistor and JESD15-4 DELPHI models) | https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7648.pdf | October 2026 |
| [IPC standards list] | Global Electronics Association, "Meet Your Standards" (IPC-6012F, IPC-A-610J, IPC J-STD-001J, IPC-4101E-WAM1, IPC/WHMA-A-620F) | https://www.electronics.org/meet-your-standards | October 2026 |
| [IPC J revisions] | IPC, "IPC Releases 'J' Revisions to Two Leading Standards for Electronics Assembly", 8 April 2024 | https://www.electronics.org/news-release/ipc-releases-j-revisions-two-leading-standards-electronics-assembly | October 2026 |
| [IPC design standards] | Global Electronics Association, "Building Electronics Better Using Design Standards" (IPC-2152, IPC-2221C, IPC-2223E, IPC-2581C, IPC-7351B, IPC-7352, IPC-D-356B) | https://www.electronics.org/ipc-design-standards | October 2026 |
| [Pollex IPC material] | Altair Pollex help, "IPC Material" (conductor-spacing categories B1 to A7 of Table 6-1) | https://help.altair.com/pollex/topics/pollex/verification/dfe_ipc_material_r.htm | October 2026 |
| [LEITON IPC-4761] | LEITON, via plugging, tenting and filling to IPC-4761 (types I to VII) | https://www.leiton.de/special-technologies-via-plugging-tenting-filling-ipc-4761.html | October 2026 |
| [IEC 62368-1] | EVS, IEC 62368-1:2023 | https://evs.ee/en/iec-62368-1-2023 | October 2026 |
| [IEC 61010-1] | EVS, IEC 61010-1:2010 with AMD1:2016 | https://www.evs.ee/en/iec-61010-1-2010 | October 2026 |
| [IEC 60601-1] | EVS, IEC 60601-1:2005 with AMD1:2012 and AMD2:2020 | https://www.evs.ee/en/iec-60601-1-2005 | October 2026 |
| [IEC 60617] | IEC webstore, IEC 60617:2026 DB, graphical symbols for diagrams | https://webstore.iec.ch/en/publication/2723 | October 2026 |
| [IEEE 315] | IEEE SA, IEEE 315-1975, inactive-reserved since 7 November 2019 | https://standards.ieee.org/ieee/315/515/ | October 2026 |
| [Wikipedia EDIF] | Wikipedia, "EDIF" | https://en.wikipedia.org/wiki/EDIF | October 2026 |
| [PathFinder award] | UW CSE News, "CSE's Carl Ebeling wins 'Top 25 in 20' from FPGA" (PathFinder, McMurchie and Ebeling, FPGA 1995), 1 March 2012 | https://news.cs.washington.edu/2012/03/01/cses-carl-ebeling-wins-top-25-in-20-from-fpga | October 2026 |
| [Grivet-Talocia 2004] | Crossref record: Grivet-Talocia, "Passivity Enforcement via Perturbation of Hamiltonian Matrices", IEEE Trans. Circuits and Systems I 51(9) (2004) 1755–1769 | https://api.crossref.org/works/10.1109/tcsi.2004.834527 | October 2026 |
| [Middlebrook 1975] | Crossref record: Middlebrook, "Measurement of loop gain in feedback systems", International Journal of Electronics 38(4) (1975) 485–512 | https://api.crossref.org/works/10.1080/00207217508920421 | October 2026 |
| [Tian et al. 2001] | Crossref record: Tian, Visvanathan, Hantgan and Kundert, "Striving for small-signal stability", IEEE Circuits and Devices Magazine 17(1) (2001) 31–41 | https://api.crossref.org/works/10.1109/101.900125 | October 2026 |
| [Dowell 1966] | Crossref record: Dowell, "Effects of eddy currents in transformer windings", Proceedings of the IEE 113(8) (1966) 1387 | https://api.crossref.org/works/10.1049/piee.1966.0236 | October 2026 |
| [IEEE 802.3ck tools] | IEEE P802.3ck, tools and channel data page (contributed channels; COM) | https://www.ieee802.org/3/ck/public/tools/index.html | October 2026 |
| [Maros-Meszaros set] | qpbenchmark, Maros-Meszaros test set (138 convex quadratic programs) | https://github.com/qpsolvers/maros_meszaros_qpbenchmark | October 2026 |
| [Optenni Lab] | Optenni, Optenni Lab | https://www.optenni.com/optenni-lab/ | October 2026 |
