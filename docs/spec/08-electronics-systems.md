# Electronics and systems (ELX)

Electrical intent in Crucible is a typed Ingot program: connectivity is a `Network` in code, a schematic is a stored drawing proved equal to it, and a board is a Part whose copper is integer layout data. Analyses return Fields with error budgets and checks with stated validity envelopes. One design repository holds schematic, board, enclosure, harness, firmware and requirements, so no exchange step can go stale.

## Scope and ownership

ELX owns connectivity and the `network { … }` builder with its element libraries, the electrical facets of catalog parts, schematic capture, the board model, layout and design-rule checking (DRC), and electrical, mechatronic, battery and power models. It also owns control design, harness connectivity, robot export and requirements traceability, in `std::electronics` and `std::systems`.

| Concern | Owner | What ELX contributes |
| --- | --- | --- |
| Network compilation, DAE and LU solvers, field solvers, the FMI runtime | FLX | Port types, element libraries, the Verilog-A front end |
| Fabrication and assembly packages, panels, stencils, rule packs, test programs | MFG | The board model; the DRC engine that runs MFG's rule packs |
| Harness 3D routing and formboard geometry | MEC | Harness connectivity, wire tables, electrical checks |
| Catalog service, registry, every `io/` reader and writer with its phase, ECAD migration | ECO | The electrical meaning of each format |
| Schematic, layout and constraint canvases; the Electronics preset (D-UIX-27) | UIX | Content drawn through `crucible:ui/canvas2d` |
| Merge driver, configuration options, 150% BOM, Items | KLN | Net partitions; `bare_board_invariant` |
| Materials, physics models, validity envelopes | COV | Equivalent-circuit and SPMe cells (contract section 13.4) |

Out of scope, stated plainly:

- Integrated-circuit and FPGA internals; chips enter only as catalog-part models.
- Regulatory verdicts; EMC, safety and radio results are screening evidence for a test lab.
- Real-time execution; hardware-in-the-loop runs outside Kiln.
- Device physics below compact models, arcs in contactors and fuses, and electrochemistry below porous-electrode theory.
- Field-life forecasts; handbooks give comparative failure rates.

Electronics has no team before the phase 1 gate beyond a two-person circuit-simulation research track (contract section 13.2). Every ELX capability therefore lands in phase 2 or later.

New electrical physics enters only through the public mechanisms in the table below (principle 1); an acoustic domain, for example, is a package declaring one port type.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| New lumped domain | Package with a port type: across, through and power expression | Power expression is not a power: compile error | ELX-O-EXT-1 | 2 |
| New device model | Verilog-A or Ingot equation element with envelope and oracle cases | Unsupported Verilog-A construct listed with file and line | ELX-O-SIM-3 | 3 |
| New analysis | Ingot feature, or Wasm component calling `crucible:ops/flux`, returning Fields and checks | Determinizer rejection | ELX-O-EXT-1 | 3 |
| New exchange format | `io/` Wasm component with a round-trip oracle | Unmapped items listed, never dropped | ELX-O-SCH-3 | 3 |

## The electrical model

### Types

ELX's domain types are built from the core types: geometry stays in Bodies and responses stay in Fields.

| Type | What it is | Relation to core types |
| --- | --- | --- |
| `Network` | Hierarchical lumped connectivity: Instances, sub-network uses, nets, ports | Core type (contract section 2); ELX owns the builder |
| `Net`, `Pin` | A node with name and class; a catalog-part terminal with type and ranges | Plain value; catalog-part facet |
| `Port` | A typed connection point; compound ports (`Power`, `I2c`, `Spi`, `UsbC`, `Can`) group roles | Records marked `#[interface]` |
| `Schematic` | Drawn topology for one `Network`: symbols, segments, junctions, labels, sheets | Data module, checked against connectivity |
| `Stackup` | Ordered layers with Materials, `Tol<Length>` thicknesses, via spans and regions | Plain value referencing Materials |
| `Layout` | Placements, tracks, arcs, vias, zones and keep-outs | Data module in integer coordinates (D-ELX-6) |
| `Footprint` | Padstacks, mask, paste, silkscreen, courtyard, pad-to-pin map | Integer data; Bodies derived |
| `CatalogSelection` | A parametric pick of a catalog part (D-ELX-3) | Pure function over pinned data |
| Bare and assembled board | The printed board; the board with its parts | A Part of kind `pcb`; an Assembly |
| Design rule | Clearance, width, impedance, delay, creepage | A check from `std::electronics::rules` |
| Responses | Waveforms, spectra, sweeps | `Field<(Ports, Time), Voltage>` and similar |

**Decision D-ELX-1:** Connectivity is Ingot code, and a schematic is a stored drawing proved equal to it. The editor writes `connect`, `tie` and `no_connect` statements to the network source and drawn topology to a `Schematic` data module, and the blocking check `schematic_matches_network` maps each drawn group to exactly one net. *Why:* agents and the code editor need text connectivity (principle 2), which merges semantically and type-checks before anything runs; atopile shows code capture works in practice [4]. *Rejected:* drawing as the source (KiCad, Altium), whose geometric connectivity merges badly; generated drawings only, which lose signal-flow layout; an unchecked stored drawing, which can disagree with the code (R4-22). (revised in round 2)

**Decision D-ELX-2:** Every use of a catalog part in a network is an Instance of the Part its definition package describes. The bare board is a Part, and the assembled board is an Assembly whose Instance placements are the footprint placements. Sub-network uses are hierarchy nodes of the `Network`; they add Assembly levels only when the designer declares a sub-assembly, such as a daughterboard. *Why:* one derived BOM view covers mechanical and electrical items, and moving a part in layout is the same edit as in the assembly. *Rejected:* a separate symbol-instance concept, which duplicates Instance and needs a sync step.

[[DIAGRAM: Electrical source model. Authored: network source, Schematic and Layout modules, Stackup, pinned catalog definitions and offers. Derived: Network and net partition, copper and laminate Bodies, bare-board Part, assembled board, product Assembly with MEC's enclosure. Arrows: editors and agents write the authored files; Kiln builds the Network and checks schematic_matches_network; Network, Layout and Stackup yield Bodies, then Part, then Assembly; enclosure geometry flows back into outline and locked placements.]]

### Writing a network

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
    n.require(dc_voltage(n.vout) in 3.3V ± 2%)
     .require(ripple_pp(n.vout, load: load) < 20mV)
}
```

The `network { … }` block is a builder like `sketch { … }`. Its `connect` statements accumulate into a partition of pins into nets, so their order never matters and repeating one is idempotent. Port-typed parameters such as `vin` become boundary ports, `port(…)` declares new ones, and nothing outside the block mutates connectivity.

### Networks in every domain

**Decision D-ELX-15:** `Network`, built with `network { … }`, is the lumped model for every physical domain: electrical, magnetic, thermal, rotational, translational, fluid and signal ports joined by the same `connect` and compiled by Flux into one DAE. *Why:* one mechanism replaces the split between circuit simulators, block-diagram tools and physical-network tools, so a motor drive (inverter, motor, shaft, gearbox, load) is one model. *Rejected:* separate formalisms per domain, which need adapters at every boundary; the round 1 type name, which the contract replaced with `Network`. (revised in round 2)

Each port type declares its across and through quantities and its power expression, and the compiler checks that the expression is a power (contract section 5). A rotational port has angular velocity across and torque in J/rad through, so their product is watts under the strong angular system, while `Nm` literals stay short. Across variables are equal at a node, through variables sum to zero, and signal ports are causal.

Flux compiles and integrates Networks (D-FLX-27), with dummy derivatives, per-mode compilation and consistent reinitialization at events. ELX supplies element libraries, including drivetrain elements built from MEC's gear records, and the electrical fast path's stamps. Each element states its envelope; lumped wiring holds while a line is under a tenth of a wavelength.

### Hierarchy, buses and ports

- **Hierarchy.** A sub-network is a feature returning a `Network`; repeated channels are loops keyed per contract section 5.
- **Buses.** A bus is a compound `#[interface]` port or a net vector (`Bus<8>`). Joining compound ports checks roles, and an incompatible join is a compile error suggesting an adapter part.
- **Global nets.** None are implicit; a design may declare `global_net("GND")` once at the top level.
- **Electrical typing.** `Power` carries a `Tol<Voltage>` range and pins carry absolute-maximum ranges. Static mismatches fail at compile time; value-dependent ones become checks.

### Net ties and merges

**Decision D-ELX-21:** Two named nets join only through an explicit `tie(net_a, net_b, at: footprint)` element, which rule checks, netlists and IPC-2581 export treat as an intended short at one place. A pin that `connect` places in two named nets fails the unwaivable rule `named_net_join`, naming the pin, both nets and both statements. *Why:* `connect` accumulates as a set union, so two branches attaching one pin to different nets would merge into a silent short (R4-03). Star grounds and Kelvin sense points need shorts a fabricator can see (R4-22). *Rejected:* letting union semantics join named nets; net ties as drawing-only symbols, which netlists and DRC cannot see.

Kiln derives each design's net partition as a node. A merged net that unions nets distinct in the base and in each side is `Conflict::NetMerge`, naming the pins, nets and Changes (contract section 7.1). Nets match by the `OpSite` of their `net(…)` call, never by name, and the rule also covers harness Networks and `std::systems` interface connections.

### Variants

**Decision D-ELX-4:** Variants are `#[configuration]` record parameters of the board or product feature, with KLN's option rules. Fitted state, part choice and values are `if` and `match` expressions on them. CI builds the sellable configurations that repository policy lists plus a pairwise covering set, and Kiln evaluates the rest symbolically for the 150% BOM. *Why:* variants reuse Kiln's caching and checks, and region, feature and assembly options follow one model (R3-18, R4-21). *Rejected:* one `Variant` enum built exhaustively in CI, exponential in the options; variant tables beside the design, a second mechanism with its own merge rules. (revised in round 2)

```
#[configuration]
pub struct Options { region: Region, lite: bool }

let r_term = resistor(120ohm ± 1%).fitted(!opts.lite)        // land pattern stays on the bare board
let modem  = match opts.region {
    Region.eu => modem_eu,                                   // both CatalogSelections require
    _         => modem_na,                                   // land_pattern: lga_52
}
```

An unfitted part keeps its land pattern and leaves the assembly BOM and placement data. The check `bare_board_invariant` reuses the 150% BOM's abstract interpretation: every branch reaching copper, drill, outline, mask or silkscreen must give one `GeometryId`, or it fails naming the configuration and item. Copper that truly differs needs a declared fabrication variant with its own bare-board Item, and each variant states paste handling for unfitted parts.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Network builder | `network { … }` returns a `Network`; `connect` is order-independent and idempotent | Type errors at compile time with fixes, such as an adapter part | ELX-O-NET-1 | 2 |
| Domain port types | Across, through and power expression; std ports for every domain in D-ELX-15 | Power expression not a power: compile error | ELX-O-NET-3 | 2 |
| Drivetrain elements | Gear ratio, mesh stiffness, couplings and bearing friction with rotational ports, parameterized from MEC's gear records | A gear record missing a parameter is a typed error naming it | ELX-O-NET-3 | 2 |
| Electrical element library | Modified-nodal-analysis stamps for passive, source, switch and controlled elements, each with an envelope | Element outside its envelope flagged with the variable | ELX-O-NET-3 | 3 |
| Hierarchy and buses | Sub-networks as features; `#[interface]` ports with roles; `Bus<N>` | Role or port mismatch is a compile error | ELX-O-NET-1 | 3 |
| Net ties | `tie(net_a, net_b, at:)`; rule `named_net_join` | Unwaivable error naming the pin, nets and statements | ELX-O-NET-2 | 3 |
| Net partition for merges | Derived partition, nets matched by provenance | `Conflict::NetMerge` with pins, nets and Changes | ELX-O-NET-2 | 3 |
| Variants | `#[configuration]` records; CI covering set; symbolic evaluation of the rest | An unbuildable configuration fails CI and is named | ELX-O-VAR-1 | 3 |
| Bare-board invariance | `bare_board_invariant` over every branch | Fails naming the configuration and the differing item | ELX-O-VAR-1 | 3 |

## Schematic capture and rule checks

### The drawn schematic

The `Schematic` module stores drawn topology, one item per line with stable ids. Segment ends lie on pins, labels, power symbols, sheet pins or other segments at explicit junctions, and no-connect flags and bus entries are items too.

```
// buck_3v3.schematic.ingot, written by the schematic editor
pub const drawing = schematic(of: buck_3v3, frame: a4, items: [
    symbol(u1, at: (60mm, 40mm), rot: 0deg, unit: A),
    symbol(l1, at: (90mm, 40mm), rot: 0deg),
    segment(s_7, from: u1.pin("SW"), to: l1.a, via: [(78mm, 40mm)]),
    segment(s_8, from: l1.b, to: junction(j_2, at: (100mm, 40mm))),
    label("3V3", at: (110mm, 40mm), on: s_8),
    power_symbol("GND", at: (60mm, 70mm)),
    note(n_01, at: (20mm, 120mm), "Keep SW node area small"),
])
```

Editor behavior follows from D-ELX-1:

1. Drawing a segment writes a `connect` into the network block that owns both pins; crossing a hierarchy boundary adds a port. Placing a label with an existing net's name writes a `connect`, and editing a label renames the net.
2. A connection made only in code renders dashed until one gesture draws it or places a label.
3. `schematic_matches_network` blocks release. A drawn group spanning two nets is `SchematicError::DrawnShort`, shown in the danger style; an item on a removed pin is `SchematicError::StaleAnnotation` with a one-click fix.
4. Moving a symbol edits only the `Schematic` module, so branches moving different symbols merge cleanly.
5. Connectivity generated by a loop is read-only in the drawing; editing it opens the generating line.

Off-page connections are labels with generated cross-references. Reference designators live in the module and change only through an explicit renumber shown as a diff; like every name, they never influence geometry (contract section 7.1). The editors run in the Electronics preset on UIX's `crucible:ui/canvas2d` world, and UIX specifies canvases, presets and frame budgets (D-UIX-27).

### Electrical rule checks

Electrical rule checks (ERC) live in `std::electronics::erc` and re-run only for the nets an edit touched; each has a severity, an explanation and a fix. A waiver is ING's `#[waive(check:, reason:, until:)]` attribute, visible in review, and a waiver whose rule no longer fires raises a warning.

| Rule family | Examples | Source of truth |
| --- | --- | --- |
| Pin-type matrix | Two push-pull outputs on a net; input without a driver | Pin electrical types |
| Topology | Single-pin net; unconnected required pin; connected no-connect pin | `Network` |
| Net joins | Named nets joined without `tie` (unwaivable) | `Network`, D-ELX-21 |
| Voltage domains | Net range outside a pin's absolute maximum; logic-level mismatch | `Tol<Voltage>` on `Power` and pins |
| Power budget | Load current above a regulator's rating; inrush beyond a fuse | Catalog specifications |
| Bus semantics | I2C address collision; missing pull-ups; shared chip-selects | Compound port roles |
| Part rules | Missing required decoupling; floating strap pin | Catalog-part design rules |
| Protection | External connector without ESD protection | Ports marked `external` |
| Differential pairs | Polarity swapped across a hierarchy boundary | Net classes |

### Netlists and import

Netlists export as SPICE, KiCad netlist and EDIF 2 0 0 [unverified]. KiCad schematics import through an `io/` Wasm component: wires become `connect` statements, the drawing becomes the `Schematic` module, and near-miss wires are listed. Other tools arrive through ECO's migration path (R4-28), which ends in the same importer.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Drawn topology | Segments, junctions, labels, power symbols, sheet pins, no-connect flags, bus entries | `SchematicError::StaleAnnotation` with a fix | ELX-O-SCH-1 | 3 |
| Drawing matches network | `schematic_matches_network`, blocking | `SchematicError::DrawnShort` fails release | ELX-O-SCH-1 | 3 |
| Labels as connectivity | Label edit renames the net; an existing name writes a `connect` | Rename onto another net's name is a typed error naming both | ELX-O-SCH-1 | 3 |
| Reference designators | Stored and stable; explicit renumber as a diff | Duplicate designator is a `Failure` naming both Instances | ELX-O-SCH-1 | 3 |
| Pin and gate swap | Within catalog swap groups, from schematic or layout, as one source edit | Swap outside a group refused with the group | ELX-O-SCH-1 | 3 |
| ERC | Checks over the `Network` and catalog data, incremental by net, with waivers | Violation with rule, location and fix; stale-waiver warning | ELX-O-SCH-2 | 3 |
| Netlist export | SPICE, KiCad, EDIF | Unsupported construct listed, never dropped | ELX-O-SCH-3 | 3 |
| Schematic import | KiCad directly; other tools through ECO's migration path | Near-miss wires and unmapped objects listed | ELX-O-SCH-3 | 3 |
| Design blocks | Sub-network plus layout fragment published as a package | A fragment that cannot place is reported; the schematic still applies | ELX-O-SCH-3 | 4 |
| Drawing output | PDF with title blocks and cross-references; lifecycle text late-bound | None expected | ELX-O-SCH-4 | 3 |

## Catalog parts

### Electrical facets

A catalog part's definition is a signed data package under `parts::<manufacturer>::…`, pinned in `ingot.lock`, and its offers are External inputs (contract section 2). ECO runs the catalog service, MEC owns mechanical facets, and ELX owns the electrical facets.

| Facet | Contents | Typed as |
| --- | --- | --- |
| Identity | Manufacturer, part number, lifecycle, package, compliance | Plain values |
| Pins | Name, electrical type, alternate functions, swap groups, ranges | `Pin` records with `Tol<Voltage>` |
| Symbols and footprints | Symbol units; land patterns with pad-to-pin map and courtyard | Data modules; `Footprint` |
| 3D body | Exact body from ECO's STEP reader, envelope Body, keep-out Body | `Body` in CAS |
| Specifications | Capacitance, ratings, saturation current, θJA, with test conditions | `Quantity<D>` and `Tol<T>` |
| Models | SPICE, Verilog-A, IBIS, IBIS-AMI, Touchstone, thermal, magnetics | References, each with a `ValidityEnvelope` |
| Reliability and rules | Failure-rate category, derating curves, datasheet layout rules | Plain values and checks |
| Offers | Price breaks, stock, lead time | External inputs |

**Decision D-ELX-5:** Supplier offers enter evaluation only as signed External inputs pinned in `ingot.lock`, changed by an explicit update whose diff shows each change, and BOM views date every offer. *Why:* stock changes hourly and principle 4 forbids reading live data, while cost checks still need prices. *Rejected:* live supplier lookups during evaluation; offers wholly outside evaluation, which hides cost from checks. (revised in round 2)

**Decision D-ELX-3:** A network element names an exact catalog part, an internal part number or a `CatalogSelection`: a pure function over pinned definition packages, plus pinned offers when it ranks by price or stock. A selection re-resolves whenever its arguments change; `crucible update parts` refreshes only the data pins, and its diff lists every substitution. *Why:* designers state intent (`1uH ± 20%`), evaluations stay deterministic, and changing the load re-picks the inductor at once (R3-28). *Rejected:* resolving only at lockfile updates, which leaves picks stale; calling a selection a `Query`, the core type for geometric selection; exact-only selection, which blocks second sourcing. (revised in round 2)

A selection that matches nothing fails with `SelectionError::NoCatalogMatch`, naming the tightest constraint and the nearest candidates; it never widens its constraints.

**Decision D-ELX-22:** An organization parts-policy package lists approved internal part numbers (KLN `Purchased` Items) with approved manufacturers, lifecycle (preliminary, approved, not recommended, obsolete) and preferred flags. A `CatalogSelection` resolves over approved parts first and reaches the open catalog only under a recorded waiver; BOM views list each internal number with its approved manufacturers. *Why:* companies design with internal numbers their parts engineers control, so open-catalog picks alone make the design, ERP and assembly BOMs disagree (R4-20). *Rejected:* manufacturer part numbers only; an approved-parts database outside the repository.

A new-part request is one Proposal creating the internal number, its facets and its approved manufacturers. MEC's fastener selection reads the same policy.

### Footprints and symbols

Land patterns follow IPC-7351B, whose 2010 edition defines three density levels per package [55][56]; IPC also publishes IPC-7352 [unverified: which document now applies]. The generators read their standard from a pinned data package naming document and edition, so a move is an explicit update with a footprint diff (R4-42).

Footprint generators (`std::electronics::footprint::qfn`, `soic`, `bga`, `chip`, `sot`) compute toe, heel and side fillets from toleranced package dimensions. KiCad generates over 78% of its footprints from data [1]; Crucible's target is 100% for standard packages.

```
let fp = footprint::qfn(
    body: (4mm ± 0.1mm, 4mm ± 0.1mm), pitch: 0.5mm, pins: 24,
    lead_len: 0.4mm ± 0.05mm, exposed_pad: (2.6mm, 2.6mm),
    density: Density.nominal, standard: land_patterns::ipc_7351b,
)
.require(paste_coverage(fp.exposed_pad) in 50% .. 80%)
```

Symbols are generated from the pin table, which is the source, as KiCad 10's CSV pin tables suggest [1]; a librarian may refine the drawn view. Alternate body styles follow IEC 60617 or IEEE 315 [unverified: current editions].

### Creating and migrating catalog parts

1. **From a datasheet.** An agent extracts values into a record Proposal, citing page and table for each. The datasheet is untrusted text, so the context carries `instruction_tainted` and the values `data_untrusted` (contract section 7.6); a human approves.
2. **From libraries.** KiCad libraries import directly. ECO's migration path brings EAGLE XML through its own importer, and Altium, CADSTAR, EasyEDA, P-CAD and Fabmaster files through KiCad 9's importers [66] run as an external tool in a pinned container.
3. **By hand.** The symbol and footprint editors write the same data modules.

Consistency checks run on every record: pins equal pads after mapping, the courtyard encloses the body, pin types match the IBIS pin list, and SPICE port order matches the pin map. Failures block publication with a `CatalogError` naming the facet.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Electrical facets | Versioned record of the facets above | A missing facet blocks only the uses that need it | ELX-O-CAT-1 | 3 |
| Consistency checks | Pins, pads, symbol, models and body agree | `CatalogError` blocks publication | ELX-O-CAT-1 | 3 |
| `CatalogSelection` | Pure over pinned definitions and offers; re-resolves when arguments change | `SelectionError::NoCatalogMatch` with nearest candidates | ELX-O-CAT-3 | 3 |
| Offers | External inputs pinned in `ingot.lock`, dated in BOM views | An offer past its validity period is labelled with its age | ELX-O-CAT-3 | 3 |
| Parts policy | Approved internal numbers first; open catalog only under a waiver | `policy.unapproved_part` fails unless a waiver names the part | ELX-O-CAT-4 | 3 |
| New-part requests | One Proposal creates the internal number, facets and approved manufacturers | Missing facets listed in review | ELX-O-CAT-4 | 3 |
| Footprint generators | Toleranced package dimensions to `Footprint` under a pinned land-pattern package | Dimensions outside a family are a typed error; `CatalogError::PinPadMismatch` | ELX-O-CAT-2 | 3 |
| Symbol generation | Pin table to symbol view | Unplaced pin listed; `CatalogError::SymbolPinMismatch` | ELX-O-CAT-1 | 3 |
| Datasheet extraction | PDF to a record Proposal with page references | Values without a source reference are rejected | ELX-O-CAT-5 | 4 |
| Library migration | KiCad, EAGLE and other libraries to catalog parts and internal numbers | Unmapped fields listed | ELX-O-SCH-3 | 3 |

## The board as a Part

### Stackup

A `Stackup` is an ordered list of layers plus the via spans a fabricator can build. Dielectric permittivity and loss are Fields over frequency fitted with a causal multi-pole Debye model, and laminate records carry IPC-4101 designations [unverified: edition]. Copper layers carry weight, `Tol<Length>` thickness, roughness and a role.

```
let stack = stackup(name: "6L-1.6mm", layers: [
    copper(L1, 35um, role: signal),     prepreg(fab::it180a_2116, 0.11mm ± 10%),
    copper(L2, 35um, role: plane(GND)), core(fab::it180a_core, 0.71mm ± 10%),
    copper(L3, 35um, role: signal),     prepreg(fab::it180a_7628, 0.2mm ± 10%),
    copper(L4, 35um, role: signal),     core(fab::it180a_core, 0.2mm ± 10%),
    copper(L5, 35um, role: plane(PWR)), prepreg(fab::it180a_2116, 0.11mm ± 10%),
    copper(L6, 35um, role: signal),
], vias: [through(L1, L6), blind(L1, L2, laser), buried(L3, L4)])
.require(total_thickness(stack) in 1.6mm ± 10%)
```

Materials and spans come from MFG's capability records (`fab::…`), so changing fabricator re-checks the board; an unbuildable span fails with `StackupError::UnsupportedSpan`. A board may hold one stackup per outline region (rigid, flex, cavity, stiffener).

**Decision D-ELX-23:** A board declares `fab_class` and `assembly_class` (Class 2, 3 or 3/A under IPC-6012 and IPC-A-610, with J-STD-001 soldering [unverified: current editions]). They select MFG rule packs for annular ring, plating and acceptability, with document editions pinned in licensed data packages. *Why:* the class changes these rules, so it must be data the checks read and the fabrication drawing states (R4-25). *Rejected:* one rule set for every class; class as a drawing note only.

MFG's fabrication-drawing generator writes ELX's class, materials, finish and impedance tolerances with the acceptance notes.

### Board geometry

**Decision D-ELX-6:** Authored layout geometry (tracks, arcs, pads, vias, zone outlines) is data in 64-bit integer nanometre coordinates per board, bounded to ±2^40 nm, with each arc as three integer points. Predicates are exact through `anvil-planar` (D-ANV-27); constructions snap conservatively, fills inward and keep-outs outward, and a reconstructed arc survives only if it passes the exact check. Bodies are derived on demand. *Why:* integer data makes DRC and fills identical everywhere, a track costs tens of bytes, and conservative snapping lets Crucible's own fills pass its exact DRC with zero tolerance (R2-23). *Rejected:* copper as B-rep Bodies, too heavy for routing; floating-point coordinates; rounding to nearest with a hidden tolerance. (revised in round 2)

Clipper2 offers integer polygon Booleans and offsets under BSL-1.0 but no arcs [47]; `anvil-planar` adds them.

| Derived Body | Representation | Consumers | Error bound |
| --- | --- | --- | --- |
| Laminate | BRep: outline extruded, holes removed | MEC fit, Flux structural, STEP | Exact |
| Copper layer *n* | Planar BRep from tracks, pads and fills | DRC, Flux, 3D view | Exact; chords within a stated tolerance (default 0.5 µm) |
| Copper solid | Copper layer extruded by its thickness | Local 3D EM and thermal zooms | As above |
| Assembled board | Laminate plus part bodies at placements | MEC, STEP AP242, IDX | The parts' import bounds |
| Envelope | Box, cylinder or prism per part | Fast clearance | Declared, conservative |

Silkscreen revision, date and serial text are late-bound placeholders, filled at output and excluded from KLN's definition digest, so assigning a revision never changes the board's definition (R4-17).

### One model with the enclosure

**Decision D-ELX-7:** The enclosure and the board live in one design repository and one Kiln graph, so ECAD-MCAD co-design needs no exchange step. Outline, holes and connector placements may be expressions of enclosure geometry, and the reverse; IDX serves only tools outside Crucible. *Why:* every exchange step can go stale; Fusion places both domains in one environment but still raises cross-domain changes as alerts that prompt synchronization [57]. *Rejected:* an internal IDX-style baseline and increment protocol, which recreates the sync problem inside one product.

```
let board = pcb(stack, outline: enclosure.face(role: pcb_shelf).inset(0.5mm))
let mount = enclosure.bosses(m3) |> holes(board, plated: false, d: 3.2mm ± 0.05mm)
place(j1_usb, at: enclosure.cutout(usb).frame.on(board.top), lock: mech)
board.require(clearance(board.assembled(), enclosure.inner_body()) > 0.5mm)
     .require(aligned(j1_usb.body.face(role: mating), enclosure.cutout(usb), tol: 0.15mm))
```

When a mechanical engineer moves the USB cutout 2 mm, the connector follows on the next rebuild and DRC flags any track now too close. A `lock: mech` placement refuses drags; if referenced geometry disappears, the rebuild fails with a typed `ResolveError` and never keeps the old placement. Height limits arrive as keep-in volumes checked against the parts' 3D bodies.

### Boards from other tools

Mechanical teams design enclosures around boards from other ECAD tools long before ELX ships layout (R4-29). ECO's readers bring IDF (outline, holes, keep-outs, part outlines and heights) and STEP boards in as a read-only board Part with Instances and designators, in phase 2 on an early 1.x train; KiCad 9 exports both [67]. MEC's enclosure checks then run against the imported board, and in phase 1 against boards imported as STEP assemblies.

IDX V6, released in December 2025, defers splines, 3D keep-outs and chamfered edges to V7 [14]. IDX baseline import arrives in phase 2; export and change proposals, each imported as a Proposal, arrive in phase 4.

### Rigid-flex and folding

A flex region carries bend lines with radius, angle and order. `anvil::fold` maps it onto cylinders with the neutral-layer offset from the flex stackup, and folded copper follows the same map. Checks follow IPC-2223 guidance [unverified: section numbers]: minimum bend radius (larger for dynamic flexing), no vias in bend zones, staggered conductors and hatched planes.

Bend strain comes from a Flux laminate shell model as a `Field<Body, Strain>`, compared with the copper fatigue curve. The flat view feeds fabrication; the enclosure assembly instantiates the folded view.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Stackup | Layers, Materials with laminate designations, `Tol` thicknesses, via spans, regions | `StackupError::UnsupportedSpan` naming the nearest span | ELX-O-BRD-1 | 3 |
| Fabrication and assembly classes | `fab_class` and `assembly_class` select pinned MFG rule packs | A class without a rule pack for the chosen fabricator is a typed error | ELX-O-BRD-1 | 3 |
| Board Bodies | Layout data to laminate, copper and assembled Bodies with bounds | A failed planar Boolean names its items; no partial board is returned | ELX-O-BRD-1 | 3 |
| Lifecycle placeholders | Revision, date and serial text late-bound at output | A placeholder outside a text item is a typed error | ELX-O-BRD-5 | 3 |
| Enclosure co-design | Outline, holes and placements as expressions of enclosure geometry; locks | `ResolveError` when referenced geometry disappears | ELX-O-BRD-2 | 3 |
| IDF and STEP board import | Read-only board Part with Instances, designators and keep-outs (ECO's reader, on an early 1.x train) | Unmapped items listed | ECO-O-26 | 2 |
| IDX V6 | Baseline import; export and change proposals as Proposals | Proposals conflicting with locks rejected item by item, with IDX responses | ELX-O-BRD-3 | 2 (baseline import), 4 |
| Rigid-flex regions | Per-region stackups and layer sets | An item in no region is a DRC error | ELX-O-LAY-1 | 4 |
| Fold | `anvil::fold` per bend line, in bend order | Radius below the rule fails; self-intersection reported with location | ELX-O-BRD-4 | 4 |
| Flex strain | Laminate strain Field per bend against the fatigue curve | Plastic copper strain flagged | ELX-O-BRD-4 | 4 |

## PCB layout

### Placement

Interactive placement edits Instance `Transform`s in the `Layout` module: drag with live DRC, push, align, flip, arrays, rooms bound to sub-networks, and replication of one channel onto its siblings by provenance. Network edits reach the board on the next rebuild with no annotation step; a removed Instance's orphaned tracks become DRC errors, never silent deletions. Placement drag and the router run in the engine process on the interactive edit lane and stream geometry each frame through `api` (contract section 7.6).

Cypress (ISPD 2025) places parts by gradient descent on wirelength, electrostatic density and a smooth net-crossing penalty [5]. It reports 1–5.9× higher routability and up to 492.3× speedup over prior tools, its code is Apache-2.0 [6], and it lacks height, thermal and critical-net terms [5].

**Decision D-ELX-8:** Automatic placement and routing are edit tools, never evaluation steps. Each use writes ordinary `Layout` edits on a branch and opens a Proposal. *Why:* evaluations stay fast and deterministic, results are reviewable diffs that agents can iterate on, and a GPU optimizer's rounding never reaches a check. *Rejected:* placement or routing as Kiln-evaluated features, which would rewrite copper after every upstream edit.

The placer, a Wasm component, adopts Cypress's formulation and adds MEC's keep-in heights, thermal spreading, decoupling-loop length, critical-net proximity and designer locks. Its density solve calls `fft_solve` through `crucible:ops/flux`, and work is ordered by canonical numbers, never names. Targets: match Cypress's published results on its open suite, and place 500 parts in under 60 s on the reference laptop.

### Design rules and the constraint manager

Design rules are checks from `std::electronics::rules` in the design source, so they diff and merge. The constraint manager is UIX's grid over them, and editing a cell rewrites the expression.

```
let hs  = net_class("ddr4_dq", nets: ddr.byte(0).dq + [ddr.byte(0).dm])
let iso = barrier("mains_to_selv", standard: iec_62368_1, insulation: Reinforced,
                  working_voltage: (peak: 420V, rms: 250V), ovc: Ovc.ii,
                  pollution: Pd.p2, material_group: Mg.iiia, altitude: 2000m)
board.rules([
    clearance(all, all) >= fab.min_space,                     // fabricator record
    width(hs, layer: outer) == impedance_width(40ohm ± 10%),  // solved from the stackup
    delay_match(hs, to: ddr.byte(0).dqs, within: 5ps),
    max_vias(hs) <= 2,
    clearance(iso.sides) >= iso.clearance(),
    creepage(iso.sides) >= iso.creepage(),
])
```

**Decision D-ELX-9:** Rule precedence follows scope specificity, and an ambiguous overlap is an error that asks for an explicit `override`. *Why:* a designer sees which rule applies to any object, and an agent cannot change behavior by reordering rules. *Rejected:* numeric priorities, which Altium uses for query rules [54] and which hide intent; a rule store beside the design (Altium's `Constraints.xml` [54]), a second source of truth.

Specificity runs from board default through layer, net class, class pair, net and net pair to object, and the constraint manager shows the winning and shadowed rules. Manufacturing limits come from MFG's rule packs.

**Decision D-ELX-24:** Creepage and clearance come from a declared isolation barrier: its end-product standard (such as IEC 62368-1, IEC 61010-1 or IEC 60601-1), insulation grade, peak and RMS working voltage, overvoltage category, pollution degree, material group and altitude. Tables are licensed data packages per standard edition [unverified: current editions]. *Why:* products are judged against their end-product standard, whose tables differ from IEC 60664-1 alone, so spacing without grade, voltage form and altitude is wrong on safety-critical boards (R4-26). *Rejected:* a voltage and pollution-degree constructor; one default standard.

Results carry the screening label, list the barriers checked, and apply slot and coating rules only where the standard permits.

### DRC

DRC is a set of checks over derived copper and holes, run by a Wasm component built on `anvil-planar`, so every platform reaches the same verdict. Kiln caches tiles, and an edit re-checks its tiles plus neighbours within the largest clearance; distances are exact, and 3D checks refine envelope Bodies only where they collide. Each violation names the rule, the shadowed rules and both objects, and suggests a fix such as "move 0.04 mm".

Targets: full DRC of a 20-layer, 10,000-net board under 10 s on the reference laptop; incremental DRC after a routing edit under 50 ms.

### Interactive routing

The router offers walkaround, push-and-shove, highlight-collisions and free-angle modes. KiCad's router shoves in an iterative loop over obstacles, with walk-back fallbacks, spring-back nodes and post-shove optimization [45]; Crucible keeps that structure and changes three things:

1. **Exact geometry.** Decisions use integer predicates, so a shove that passes in the router passes DRC.
2. **Rule-aware cost.** Costs read the rule set, including delay budgets; a shove that would push a matched net out of its window is refused, with the reason at the cursor.
3. **Recorded sessions.** Every gesture is recorded with its inputs, and UIX-O-ELX-1 replays ELX's sessions frame by frame.

Targets: under 16 ms per pointer update with up to 50 shoved items; finishing a route writes one Change within 50 ms.

### Length and delay tuning

Constraints may be stated in length or time, as KiCad 10 allows with per-layer profiles [1], but Crucible computes delay from physics. A cached Flux solve per cross-section gives delay over frequency, and stackup tolerances make each net's delay a `Tol<Time>`, matched worst case. Via and package delays come from per-via solves and IBIS package data, and tuning patterns keep self-coupling under a stated limit.

### Autorouting

**Decision D-ELX-10:** The autorouter is a search-based router shipped as a public Wasm component. It runs escape routing by flow, negotiated-congestion global routing, gridless A* detailed routing, rip-up and reroute, then shove cleanup and via minimization. Learned models may supply cost hints through a Wasm component interface but never decide legality. *Why:* PCBWorld, an engine-grounded benchmark of 679 real boards, reports that learning-based routing still lags rule-based routers [30], and a search core is deterministic and explainable. *Rejected:* an end-to-end learned router, unproven and hard to review; linking Freerouting, which is GPL-3.0 [35] and stays an external baseline over Specctra DSN and SES.

Global routing follows PathFinder (McMurchie and Ebeling, 1995 [unverified]). Allegro X AI claims a 10× or greater turnaround reduction [40], and Quilter generates candidate boards by reinforcement learning under physics checks [41]; both claims are vendor-stated. Target: beat Freerouting's completion and via count on PCBWorld-Bench at equal or lower runtime.

### Pours, planes and vias

**Decision D-ELX-11:** Zone fills are derived on every rebuild, never stored, and snap conservatively away from obstacles. *Why:* a stale fill is a known way to ship shorts or missing connections, and integer clipping by tile makes fills reproducible and fast. *Rejected:* stored fills refilled by hand before output. (revised in round 2)

- **Zones** have an outline, net, layers, priority, clearance, thermal reliefs, island policy and solid or hatched fill; equal-priority overlaps are an error.
- **Plane splits** are zones on plane layers; a check flags signals crossing a gap in their reference plane.
- **Vias** cover through, blind, buried and stacked or staggered microvias, via-in-pad, back-drilling with a stub rule, stitching fences and teardrops, within the fabricator's HDI limits.

### Test points and the manufacturing handoff

`test_point(net, pad:, side:, min_pitch:, keepout_height:)` adds probe access, and an automatic Proposal adds test points to nets without access (R4-25). Test-point checks and MFG's test programs both land in phase 3, because GP5 is assembled then (R4-24).

MFG owns the factory handoff (R3-25, R4-24, R4-27): package choice, panels, stencils, rule packs, DFM, DFA and test programs. ECO owns every format writer and its phase: IPC-2581C, Gerber X2 and X3 at revision 2026.05 [15][16][17], drill files and ODB++ arrive in phase 3, with KiCad 9's ODB++ export [65] as an external oracle. ELX supplies the board model the writers read and shows their findings, including IPC-2581C fabricator feedback [19], on the objects they name.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Interactive placement | Instance `Transform` edits with live DRC on the interactive edit lane | Overlaps shown live; the edit is allowed and flagged | ELX-O-LAY-3 | 3 |
| Automatic placement | Placer to a Proposal (D-ELX-8) | Infeasible constraints named; a partial result is labelled partial | ELX-O-LAY-5 | 4 |
| Constraint manager | Grid over rule declarations with specificity precedence | Ambiguous overlap requires `override` | ELX-O-LAY-6 | 3 |
| Isolation barriers | Creepage and clearance per declared standard, grade and conditions | A barrier without a standard is an error | ELX-O-LAY-6 | 3 |
| DRC | Exact checks over derived geometry, incremental by tile | Violation with rule, shadowed rules, objects and fix | ELX-O-LAY-1 | 3 |
| Interactive routing | Walkaround, shove, highlight; 45°, 90°, free angle and arcs; differential pairs; drag | The head stops at the last legal point and shows the blocker | ELX-O-LAY-3 | 3 |
| Multi-track routing and fanout | Group routing at rule pitch; BGA and QFN escape | Members that cannot follow stop separately; unescapable pins listed | ELX-O-LAY-3 | 4 |
| Delay tuning | Field-solved delay as `Tol<Time>`; tuning patterns | An unachievable match reports the shortfall | ELX-O-SI-1 | 3 |
| Autorouting | Router to a Proposal | Unrouted connections listed; no Proposal carries DRC errors | ELX-O-LAY-4 | 4 |
| Zones, fills and teardrops | Derived on every rebuild, conservatively snapped | Equal-priority overlap is an error; islands handled per policy | ELX-O-LAY-2 | 3 |
| Vias and HDI | Spans from the stackup and the fabricator record | A disallowed span or stack is refused with the rule | ELX-O-LAY-1 | 3 (through, blind, buried), 4 (microvias, HDI) |
| Test points | `test_point` features; Proposals for nets without access | Untestable nets listed | ELX-O-LAY-7 | 3 |
| Board data for manufacturing | Board model read by ECO's writers for MFG's packages; findings on board objects | A construct a writer cannot express is listed by that writer | ELX-O-DET-1 | 3 |

## Electrical analysis

Every analysis is an Ingot feature that builds a Flux problem or calls a solver Wasm component. It returns Fields with an `ErrorBudget` and a `ValidityEnvelope` at `Interactive` or `SignOff` fidelity, and Kiln re-runs only the analyses an edit touches. Screening results carry a screening label and never stand as compliance.

[[DIAGRAM: Electrical analysis dataflow. Left: Network, Layout, Stackup, catalog-part models. Middle: derived copper and laminate Bodies, cross-section cache. Right: RLGC, channels, PDN, IR drop, EMC screening, board thermal and circuit simulation, producing Fields with budgets and checks for CI. Feedback: part power into board thermal; temperature back into simulation and IR drop. External Ops (IBIS-AMI, ngspice) sit on the untrusted-worker side.]]

### Signal integrity

Impedance and RLGC come from a 2D quasi-static Flux solve per cross-section with conductor loss, roughness and causal dielectrics, valid below a tenth of a wavelength. Post-layout extraction splits nets into lines, vias and discontinuities, and crosstalk covers aggressors within a reported window. S-parameters use Touchstone 2.1 [20].

Macromodels use vector fitting (Gustavsen and Semlyen, 1999 [52]) with residue perturbation for passivity, as the SINTEF toolbox does [52], and a Hamiltonian test [unverified: citation]; fit error enters the `ErrorBudget`. Fitting runs on `linalg`, since faer (MIT [48]) runs only in `CpuIsa` (contract section 7.1).

Channel simulation offers statistical eyes and bit-by-bit runs with IBIS 8.0 buffers, ratified on 5 December 2025 [21], and IBIS-AMI equalization; IBIS-ISS is at 1.0, and the parser is validated against IBISCHK8 [20].

**Decision D-ELX-12:** IBIS-AMI executables run only as External Ops on untrusted-evaluation workers, in a pinned host image per vendor platform (contract section 7.8). Results carry the host's class or `Unverified`, releases pin their `ObjectId`s, and a missing platform build is reported, never emulated. *Why:* AMI models are vendor-compiled native libraries that cannot be determinized, and native code beside attestation keys would let one escape poison the shared cache (R5-03). *Rejected:* loading AMI libraries into the engine process; running them on trusted builders. (revised in round 2)

### Power integrity

Target impedance per rail is allowed ripple over transient current. PDN impedance comes from Flux's layered sheets solving the Helmholtz equation per plane pair, coupled through via, capacitor and regulator models, with a full-wave solve suggested above the plane-pair limit. Decoupling optimization picks capacitor types, counts and sites by greedy insertion and local search.

IR drop solves DC conduction on per-layer copper sheets joined by via and plating resistances, beside an IPC-2152-based current-capacity screen [unverified: edition]. Electro-thermal coupling is phase 4 (contract section 13.4): Flux uses monolithic Newton with continuation and reports `Runaway { power }` at the turning point (R1-49).

### EMC and EMI

ELX builds excitations and geometry; Flux solves the fields.

- **Radiated emissions.** Common- and differential-mode currents become current Fields on copper, and Flux's FDTD (D-FLX-32) computes far fields at 3 m or 10 m with the enclosure, cables and harness in the model.
- **Conducted emissions.** A line impedance stabilization network sits in the simulation, with hot-loop parasitics from Flux extraction.
- **Immunity and ESD.** Port-level transient injections rank vulnerable nets.
- **Rule screening.** Every rebuild checks return-path breaks, slots under clocks, unstitched plane edges, long stubs and missing ground vias.

### Board thermal

Part power comes from simulation averaged over a stated window, a declared operating mode or datasheet values, labelled by source. Packages use two-resistor or DELPHI compact models per JEDEC JESD15 [unverified: part numbers], or the full package Body.

**Decision D-ELX-26:** At `Interactive` the board uses orthotropic conductivity per layer and tile from copper coverage; at `SignOff` it uses 2.5D layered conduction (per-layer thin sheets plus through-plane conductance) sharing the IR-drop machinery. Explicit 3D copper serves only local zooms. *Why:* 35 µm copper on a 100 mm board is a 3,000:1 scale ratio over thousands of traces, which no volumetric octree resolves (R1-49). *Rejected:* explicit copper for the whole board; effective conductivity at `SignOff`, which hides hot spots under thin traces.

Convection and the enclosure come from Flux conjugate heat transfer, laminar in phase 3 and turbulent in phase 4 (contract section 13.4). Outputs are a `Field<Body, Temperature>` and junction temperatures as a `Field<Instances, Temperature>`, checked against limits and derating rules and fed back to simulation and IR drop.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Impedance and RLGC | Cross-section solve to `Field<Frequency, Rlgc>` with tolerance bands | Beyond the quasi-TEM limit flagged; a dielectric without frequency data names the Material | ELX-O-SI-1 | 3 |
| Post-layout extraction and crosstalk | Nets to S-parameters per net group; NEXT and FEXT within a reported window | An unmodelled discontinuity falls back to a full-wave solve, with its cost reported | ELX-O-SI-1 | 4 |
| S-parameter macromodels | Touchstone data through ECO's codec; vector fitting with passivity enforcement | Non-passive or non-causal data flagged per frequency; failed fit reports its worst error | ELX-O-SI-2 | 4 |
| Pre-layout topology and channels | Topologies and routed nets to eyes, timing and BER contours | A non-linear channel in statistical mode is refused; a missing AMI build is reported | ELX-O-SI-3 | 4 |
| Target impedance and PDN | Masks per rail; plane-pair solve with capacitor, via and regulator models | Missing load data leaves the check `Undecided`; beyond the plane-pair limit flagged | ELX-O-PI-1 | 4 |
| Decoupling optimization | Proposal with placements and impedance before and after | An infeasible mask reports the best achievable impedance and failing band | ELX-O-PI-1 | 4 |
| IR drop and current capacity | Thin-sheet DC conduction per layer; IPC-2152 screen | Limit exceeded fails with location, value and limit | ELX-O-PI-1 | 3 |
| Electro-thermal coupling | Monolithic Newton with continuation (FLX) | `Runaway { power }` at the turning point | ELX-O-PI-2 | 4 |
| Emissions screening | Current Fields to far fields against limit lines; conducted emissions with a LISN model | Screening label; a missing cable or enclosure is listed as an assumption | ELX-O-EMC-1 | 4 |
| Immunity and ESD screening | Ranked vulnerable nets | Screening label | ELX-O-EMC-1 | 5 |
| Return-path and EMC rule screening | Geometric checks on every rebuild | Violations with locations | ELX-O-EMC-1 | 3 |
| Board thermal | Part power to temperature and junction Fields (D-ELX-26) | Estimated power labelled; a part without a thermal model uses θJA with a warning | ELX-O-TH-1 | 3 |

## Analog and mixed-signal simulation

### Engine choice

| Engine | Licence and note | Role |
| --- | --- | --- |
| ngspice | BSD-3-Clause core with LGPL-2 and GPL-2+ files [8] | Vendor-model engine and reference (External Op) |
| VACASK | AGPL-3.0; 57.98 s on C6288 against ngspice's 71.81 s and Xyce's 151.57 s, authors' figures [9] | Cross-check |
| Xyce; OpenVAF | GPL-3.0 [60][10]; OpenVAF emits native OSDI objects | Cross-check; not linked |
| Crucible engine | Apache-2.0 WITH LLVM-exception, Rust | Native and Verilog-A models, Monte Carlo, adjoints |

**Decision D-ELX-13:** Crucible's circuit simulator is written in Rust as Flux operations: modified nodal analysis, Newton with homotopy fallbacks, and BDF 1 and 2 or trapezoidal integration with truncation-error control. It factors with Flux's block-triangular LU in the canonical `linalg` crate (the KLU scheme, reimplemented). Analyses are `F64Required`, and Monte Carlo runs one sample per CPU SIMD lane. *Why:* the engine must run in Wasm, return Fields and give adjoints through Flux's derivatives; faer's runtime cache blocking breaks the canonical class (R1-10), and junction currents need `f64` (R1-39). *Rejected:* linking ngspice (LGPL and GPL-2+ files [8], no derivatives or Wasm parity); VACASK and Xyce (AGPL and GPL [9][60]); `f32` GPU batching. (revised in round 2)

SPICE3 device models (diode, Gummel-Poon BJT, JFET, MOSFET levels 1 to 3, VDMOS) are ported from ngspice's BSD-3-Clause code with attribution [8], each enabled after matching ngspice on a regression corpus.

**Decision D-ELX-14:** Crucible's Verilog-A front end, a public Wasm component, lowers compact models to the shared kernel IR, whose Verilog-A constructs join in phase 3 (contract section 7.5). The IR emits canonical CPU and Wasm kernels with derivative Jacobians, keyed by source, front-end version and target. *Why:* BSIM, PSP, VBIC and many vendor models ship as Verilog-A, and one IR gives native speed, browser parity and a fixed operation order. *Rejected:* OSDI shared objects, native and platform-specific; Wasm-only device models, which lose derivatives and the fixed order. (revised in round 2)

**Decision D-ELX-25:** Imported vendor models run by default in ngspice as an External Op labelled with its host, and move to the native engine only after matching ngspice on their own test bench. Encrypted models never run natively; they run only in their vendor's engine as an optional External Op where the user holds a licence [unverified: batch-use terms]. *Why:* designers judge a simulator by whether vendor models run, and ngspice has added PSpice and LTspice compatibility over many releases [68] (R4-23). *Rejected:* listing vendor dialect constructs as unsupported until the native engine catches up; decrypting models.

The netlist importer reads ngspice, PSpice and LTspice dialects, lists unsupported constructs with file and line, and stores imported text for review.

### Analyses and results

Simulation results carry an `ErrorBudget`: temporal and algebraic errors `Estimated` from truncation control and residuals, input error from `Tol` propagation, and model form `NotQuantified` unless a device envelope cites a validated bound. A check on them is therefore a conditional `Pass`, meeting a release gate only under a policy naming a covering allowance (contract section 5).

Monte Carlo draws from `Tol` distributions with ING's correlation groups, so parts from one reel move together. Random streams are keyed by the class-independent part of the `OpKey` and the sample index (contract section 7.2), so added samples never change earlier ones.

Targets:

- 95% of an unencrypted vendor-model corpus parses, converges and matches the vendor's reference engine within 1%.
- Regression results lie within relative 10⁻³ or absolute 1 µV of ngspice.
- C6288 with PSP103.4 models runs within 1.2× of VACASK's time.
- 10,000 samples of a 200-node circuit's AC response take under 60 s on the reference laptop's CPU.

### Mixed-signal

An event-driven digital kernel in the style of XSPICE provides four-state logic with threshold and hysteresis bridges, and digital events become analog breakpoints. Verilog blocks compile with Verilator (LGPL-3.0 or Artistic-2.0 [29]) and run as External Ops; microcontrollers run real firmware in Renode (D-ELX-18).

### Reliability prediction and derating

Reliability prediction gives failure rates for comparison and allocation, and every result names its handbook because handbooks disagree by large factors.

| Method | Edition | Use |
| --- | --- | --- |
| FIDES | Guide 2022 Edition A; registration required [59] | Default for new designs |
| Telcordia SR-332 | Issue 4, March 2016 [58] | Telecom |
| MIL-HDBK-217F | Notice 2 [58] | Legacy and defence |
| IEC 61709 via SN 29500 | Reference conditions converted to operating ones [58] | Industrial |
| Physics of failure | Engelmaier and Coffin-Manson solder fatigue on Flux strain; Black's equation; Arrhenius wear-out | Critical joints and parts |

Crucible ships the engines; handbook tables are licensed data packages outside the public registry. Mission profiles are Ingot values, so part stresses per phase come from simulation and thermal results. Derating follows ECSS-Q-ST-30-11C [unverified: edition] and NAVSEA SD-18 [unverified], and fault trees from the `Network` hierarchy feed FMEA tables in `std::systems`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operating point | Newton with damping; gmin, source stepping and pseudo-transient homotopy in order | Non-convergence returns the largest-residual nodes and a fix, such as a missing DC path | ELX-O-SIM-1 | 3 |
| DC sweep | Continuation over a source value to `Field<(Ports, Voltage), Current>` | As operating point, per point | ELX-O-SIM-1 | 3 |
| AC and noise | Linearized complex LU per frequency to `Field<(Ports, Frequency), Complex<Voltage>>`; adjoint noise | A singular matrix names the floating node set | ELX-O-SIM-1 | 3 |
| Transient | BDF and trapezoidal with LTE control, breakpoints, ringing detection, to `Field<(Ports, Time), Voltage>` | `StepTooSmall` with time, device and nodes | ELX-O-SIM-1 | 3 |
| Pole-zero and loop stability | Generalized eigenvalues; Middlebrook or Tian loop gain [unverified: citations]; margins | As AC | ELX-O-SIM-1 | 3 |
| Monte Carlo and corners | `Tol` samples with correlation groups, one per SIMD lane | Failed samples counted and reported, never dropped | ELX-O-SIM-4 | 3 |
| Sensitivity and worst case | Adjoint DC, AC and transient sensitivities; corner search confirmed by simulation | None beyond the analysis | ELX-O-SIM-4 | 4 |
| Periodic steady state and harmonic balance | Shooting Newton; harmonic balance for mixers and amplifiers | Divergence with iteration history | ELX-O-SIM-1 | 5 |
| Vendor models | ngspice External Op; migration to native after a matched test bench | Host failure is a `Failure` with the host log; worker loss is an Abort | ELX-O-SIM-2 | 3 |
| Verilog-A compact models | Front end to the kernel IR | Unsupported construct listed with file and line | ELX-O-SIM-3 | 3 |
| Mixed-signal | Event kernel and bridges; Verilator External Ops | Unsupported HDL construct listed | ELX-O-SIM-5 | 4 |
| Reliability and derating | Handbook engines over licensed tables; physics of failure; mission profiles | A missing table leaves the check `Undecided` with the reason | ELX-O-REL-1 | 4 |

## Mechatronics

### Electric machines

Machines come at three model levels (COV), each a `Network` element with rotational and electrical ports, so a drive simulation changes model level without rewiring.

| Model level | Model | Use |
| --- | --- | --- |
| L1 lumped | dq model with flux-linkage saturation tables over (id, iq, θ), iron-loss resistance, thermal network | Systems and controls |
| L2 reduced map | Flux-linkage, torque and loss maps from batched Flux magnetostatic solves | Drive design, efficiency maps, tuning |
| L3 field | Transient magnetodynamics with motion and eddy currents, coupled to the drive Network | `SignOff`: ripple, cogging, losses, demagnetization |

Machine features build laminations, slots, star-of-slots windings and magnets for permanent-magnet, induction, reluctance, axial-flux and linear machines. Pyleecan is Apache-2.0 but couples to FEMM, which it supports only on Windows [44], so Crucible solves machine magnetics in Flux.

**Decision D-ELX-16:** Efficiency and loss maps come from Flux magnetostatic solves with motion handled by Flux's sliding interface or mortar coupling, capturing saturation per (id, iq) point. Points solve in parallel and cache individually. *Why:* map points are independent, so Kiln reuses every point after an edit that changes only the control strategy. *Rejected:* analytic machine models only, which miss saturation and slot effects; one transient solve per operating point, far costlier than a map needs.

Solenoids and voice coils use magnetostatic force maps; piezo stacks use Flux's piezoelectric model with a Butterworth-Van Dyke lumped equivalent.

### Sensors and drives

A sensor has three layers: optional Flux transduction physics, such as a Hall element in a magnet's field; a behavioral element with transfer, noise, drift and quantization; and a register interface from CMSIS-SVD or SystemRDL [unverified: Renode support for both]. Its error budget is a check over the three, such as encoder angle error under 0.1°.

Inverters range from averaged models to switching models with losses from catalog switching-energy curves. ELX's drivetrain elements, parameterized from MEC's gear records, let GP3's gearbox and a lumped motor form one drivetrain from phase 2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Machine geometry features | Typed parameters to machine Bodies and winding layout | Slot overlap or negative tooth width is a typed error | ELX-O-MCH-1 | 4 |
| Lumped machine model | dq element with saturation tables | Operation outside the tables is flagged, never extrapolated | ELX-O-MCH-1 | 4 |
| Flux-linkage, torque and loss maps | Batched magnetostatic solves with interpolation error | Unconverged points marked in the map | ELX-O-MCH-1 | 4 |
| Transient machine `SignOff` | Magnetodynamics with motion coupled to the drive Network | Divergence reported with time and region | ELX-O-MCH-1 | 4 |
| Actuators | Force maps and lumped equivalents | As machine maps | ELX-O-MCH-2 | 4 |
| Sensor models | Three layers with an error budget as a check | A missing layer leaves the budget `Undecided` | ELX-O-MCH-2 | 4 |
| Drive models | Averaged and switching inverters with losses | Missing switching curves listed | ELX-O-MCH-2 | 4 |
| Drivetrain coupling | ELX's drivetrain elements with ideal sources or a lumped DC motor in one Network | Port domain mismatch is a compile error | ELX-O-NET-3 | 2 |

## Controls and co-simulation

### Representations

Control design uses plain Ingot values, with no separate block-diagram language.

| Representation | Type | Operations |
| --- | --- | --- |
| Transfer function | `Tf<In, Out>` over s or z, `Quantity` coefficients | Feedback, discretization (ZOH, FOH, Tustin), minimal realization |
| State space | `Ss<In, Out>` with typed signals | Controllability, observability, balanced truncation |
| Frequency response | `Zpk`; `Field<(Ports, Frequency), Complex<Ratio>>` for measured data | Bode, Nyquist, Nichols, margins |
| Block diagram and hybrid | A `Network` of signal ports; state machines with typed events | Flattening to state space; event detection |

A gain from a position error in metres to a torque has type `Quantity<Torque / Length>`, so a missing conversion fails at compile time. Plants come from linearized Flux multibody models of MEC assemblies, Networks and reduced Flux models. A Flux structural mode becomes a plant pole pair, so GP6's attitude loop is checked against frame resonances. Controllers export as C with a harness that matches the Ingot reference bit for bit, and the code is a Software item.

### Co-simulation

**Decision D-ELX-17:** An FMU instance is a `Network` element whose ports and units come from its model description, and Flux's FMI 3.0.2 and SSP 2.0.1 runtime executes it (D-FLX-30). ELX also owns bus simulation over FMI-LS-BUS. *Why:* one runtime ends round 1's duplicate FMI specifications (R3-24), while FMUs still join drives and plants through ordinary `connect`. *Rejected:* a second FMI master in ELX; FMUs outside the Network model. (revised in round 2)

FMI 3.0.2 is a maintenance release [12], SSP 2.0 supports FMI 3.0 and virtual ECUs [13], and SSP 2.0.1 is current [11]; FMU export and SSP are phase 4 (contract section 13.4). FMI-LS-BUS 1.0 (21 July 2025) covers the CAN family [26], a 1.1 beta adds FlexRay and Ethernet [26], and 1.3 adds LIN, in beta since June 2026 [27].

Modelica arrives through FMUs. The Modelica Standard Library is BSD-3-Clause, v4.1.0 since 23 May 2025 [61]; OpenModelica's OSMC-PL 1.8 means AGPL-3.0 for non-members [63], so it runs only as an external tool. Rumoca, an Apache-2.0 Rust compiler its authors call rough-edged [50], is a phase 5 option feeding Flux's Network compiler, whose approach follows ModelingToolkit [51].

### Firmware-in-the-loop

**Decision D-ELX-18:** Renode is the default firmware emulator and QEMU the alternative for application processors; both run as External Ops on untrusted-evaluation workers. Renode is MIT, runs unmodified binaries on Arm, RISC-V, x86, Xtensa and other cores, models multi-node networks [28] and co-simulates RTL through Verilator [62]. *Why:* a permissive licence, broad microcontroller coverage and scriptable peripherals; firmware is untrusted native execution, so it never shares a host with attestation keys (R5-03). *Rejected:* a Crucible emulator, duplicating a mature effort; single-family vendor simulators; emulators in the engine process. (revised in round 2)

1. **Peripheral bridge.** Pins, ADCs, timers, PWM outputs and serial buses map to nets or signal ports from the pin facet and the firmware's board description, checked on every rebuild.
2. **Lock-step time.** Emulator and network advance in quanta (default 10 µs); PWM edges and ADC samples cross as timestamped events, and results report the timing error the quantum allows.
3. **Determinism.** With fixed quantum, seeds and peripheral models, runs repeat, and the ELF hash enters the key. Renode describes its environment as deterministic [62]; Crucible verifies it per release.
4. **Tests.** DWARF variables appear beside circuit signals, and firmware tests are checks, such as `require(settle_time(motor.speed, to: 3000rpm, within: 2%) < 150ms)`.

### Hardware-in-the-loop

Real-time execution lies outside Kiln, so Crucible provides hooks and evidence: plants export as FMUs or fixed-step C, and bench adapters are external programs talking to `api`. A run is an Evidence record signed with a TPM-held device key (contract section 7.1), never a cached result. On a rig under an `unattended_safe` site policy, flashing and running the board is the `run_rig_test` Act, whose approved plan digest covers the firmware image; on any other bench a person flashes the board and enables outputs (contract section 7.6).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Transfer-function and state-space algebra | Typed signals, discretization, realization | Unit mismatch around a loop is a compile error | ELX-O-CTL-1 | 4 |
| Linearization | Exact Jacobians of the plant DAE through Flux derivatives | A non-smooth operating point (contact, saturation) is flagged | ELX-O-CTL-1 | 4 |
| PID tuning | Constrained optimization of a margin objective over a stated uncertainty set | Infeasible margins: the best achieved margins are reported | ELX-O-CTL-1 | 4 |
| LQR, LQG and Kalman filters | Schur-method Riccati solvers on `linalg` | Uncontrollable or undetectable modes reported | ELX-O-CTL-1 | 4 |
| System identification | Prediction-error and subspace (N4SID) methods | Poor fit reported with residual whiteness tests | ELX-O-CTL-1 | 4 |
| Model order reduction | Balanced truncation with an a priori H∞ bound; Krylov for large plants | Bound reported with the reduced model | ELX-O-CTL-1 | 4 |
| H∞ and µ synthesis | Structured H∞ by nonsmooth optimization; LMIs through a conic solver | Infeasible bound: best achieved norm reported | ELX-O-CTL-1 | 5 |
| Model predictive control | Condensed or sparse QP through Clarabel (Apache-2.0 [49]) or ADMM | Infeasible QP reported with active constraints | ELX-O-CTL-1 | 5 |
| Controller code generation | Fixed- or floating-point C with a bit-exact harness; a Software item | Overflow reported with signal and input | ELX-O-CTL-1 | 4 |
| FMU elements | FMU instance as a Network element (FLX runtime) | Unmappable unit or variability is a typed import error | ELX-O-CTL-2 | 4 |
| Bus simulation | FMI-LS-BUS for the CAN family; LIN and Ethernet as the standard matures | Unsupported bus features reported | ELX-O-CTL-2 | 5 |
| Firmware-in-the-loop | ELF and board description to traces and checks, in lock-step | Pin-map mismatch is a `Failure`; an unsupported peripheral refuses the run | ELX-O-FW-1 | 4 |
| RTL co-simulation | Verilator models through Renode | Unsupported bus protocol reported | ELX-O-FW-1 | 5 |
| Hardware-in-the-loop | Plant FMUs or fixed-step C out; Evidence records in | Variable-step constructs refused; evidence on an incompatible version does not count | ELX-O-FW-2 | 4 |

## Batteries and power electronics

### Cell models

Cell models form a ladder, each rung with its envelope. Parameter sets are Materials (COV) whose fitting conditions become part of the envelope.

| Model | Equations | Valid for | Phase |
| --- | --- | --- | --- |
| Equivalent circuit | OCV(SOC, T), R0 and RC pairs; a hysteresis state for LFP [unverified: reference model] | Pack and BMS design in the fitted range | 4 (contract section 13.4) |
| SPMe | One particle per electrode plus electrolyte transport | Moderate rates | 4 (contract section 13.4) |
| DFN (P2D) | Porous-electrode theory over a particle-radius domain (D-FLX-38) | High rates, plating risk | 5, FLX (contract section 13.4) |
| Swelling and stack pressure | Expansion against state of charge with pad stiffness [unverified: reference model] | Within the tested pressure range | 4 (contract section 13.4) |
| Degradation | SEI growth, plating, loss of active material | Within the tested conditions | 5 |
| Abuse mechanics | Homogenized jelly roll with failure strain, coupled to runaway screening [unverified: reference model] | Crush, penetration and crash screening | 6 (contract section 13.4) |

**Decision D-ELX-19:** Equivalent-circuit cells are Network elements and SPMe cells are Flux forms, both owned here (contract section 13.4). DFN cells use Flux's parameter-domain forms (D-FLX-38), and pack-scale models embedding them follow in phase 6. PyBaMM is the reference for oracles and parameter sets. *Why:* PyBaMM is BSD-3-Clause and provides SPM, SPMe and DFN with SUNDIALS solvers [42][43]; native models give derivatives for fitting, Wasm portability and coupling to Flux thermal Fields. *Rejected:* embedding PyBaMM, which puts a Python runtime in evaluation; DFN as an ordinary form, which needs nested domains the form language lacked (R1-24). (revised in round 2)

### Pack design

A pack is an Assembly of cell Instances, busbars, a BMS board and an enclosure, and ELX adds its electrical meaning:

- **Topology.** A `14s4p` arrangement generates the Network, each cell perturbed by its own parameters.
- **Busbars.** Flux DC conduction gives resistance and Joule heat; joint resistance is an element with stated uncertainty.
- **BMS.** A board designed here, whose functions run as models or as real firmware.
- **Thermal and swelling.** Cell heat goes to Flux conjugate heat transfer; swelling sets pad compression and stack-force checks (R1-40).
- **Safety.** Fuse coordination, isolation barriers (D-ELX-24) and runaway propagation screening from published calorimetry.

### Power converters and magnetics

`std::electronics::power` provides buck, boost, flyback, forward, LLC, full-bridge, dual-active-bridge, PFC and inverter features returning Networks. Averaged models give part stresses that become `CatalogSelection` constraints; losses become power Fields, and hot-loop inductance from Flux extraction bounds switch-node overshoot.

| Quantity | `Interactive` method | `SignOff` method |
| --- | --- | --- |
| Core loss | iGSE with DC-bias correction; MagNet-trained models where available | Same, with flux waveforms from a Flux solve |
| Winding loss | Dowell (1966) [unverified: citation]; Albach and Lammeraner for round wire, Albach and Ferreira for Litz [53] | 2D or 3D Flux eddy-current solve of the window |
| Inductance and leakage | Reluctance network with Roshen fringing and Zhang gap reluctance [53] | Flux magnetostatic solve |
| Capacitance and thermal | Albach winding capacitance [53]; thermal network | Flux electrostatic solve; conjugate heat transfer |

The MagNet Challenge 2023 benchmarked data-driven magnetics models, reporting large gains in accuracy and size in 2025 [39]; Crucible adopts its dataset and metric. OpenMagnetics MKF is MIT [53] and a candidate for porting. A designed transformer gets an item number and a BOM like any Part.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Equivalent-circuit cells | OCV, resistance, RC pairs and optional hysteresis as a Network element | Operation outside the parameter set's range is flagged with the variable | ELX-O-BAT-1 | 4 |
| SPMe cells | Forms with a parameter-set Material, to voltage, temperature and concentration Fields | As above | ELX-O-BAT-1 | 4 |
| Parameter fitting | Measured data to a set with confidence intervals | Unidentifiable parameters reported, never fixed silently | ELX-O-BAT-1 | 4 |
| Swelling and stack pressure | Expansion and pad stiffness to pressure and force Fields | Outside the tested pressure range flagged | ELX-O-BAT-2 | 4 |
| Pack Network, busbars and thermal | Series-parallel layout with per-cell variation; Flux conduction and heat transfer | Inconsistent count or orientation is a compile error; limits fail checks | ELX-O-BAT-2 | 4 |
| Pack safety screening | Fuse coordination, barriers, runaway propagation | Results labelled as screening | ELX-O-BAT-3 | 6 |
| Abuse mechanics and pack-scale DFN | Jelly-roll failure model coupled to runaway screening; DFN cells in pack thermal | Outside the envelope the zone is `Invalid` and checks refuse | ELX-O-BAT-3 | 6 |
| Converter topologies and loops | Parameters to Networks with selection constraints; compensators with margins | An infeasible duty cycle is a typed error; an unstable loop fails with its margins | ELX-O-PWR-1 | 4 |
| Losses and parasitics | Loss Fields; hot-loop inductance from Flux extraction | Missing loss curves leave the check `Undecided` | ELX-O-PWR-1 | 4 |
| Magnetics design | Core, winding and gap to losses, inductances and Bodies | Saturation at peak current fails the check | ELX-O-PWR-2 | 4 |

## Wire harnesses

MEC owns 3D routing and formboard geometry, ELX owns connectivity, wire tables and electrical checks, and MFG owns the harness manufacturing package (R4-30). Connectivity, wire tables, the formboard and VEC export land in phase 4 because GP6 needs them; MEC's phase 3 routing uses declared bundle diameters until then.

- **Connectivity.** A harness is a `Network` of connector, wire, splice and terminal catalog parts joined to board ports by `connect`, so harness and boards form one netlist.
- **Wire table.** Per variant: ends, gauge, colour, cut and strip lengths, terminal and seal part numbers, and crimp height and pull force from the terminal maker's data.
- **Lengths.** MEC's routed paths plus service loops and termination allowances.
- **Checks.** Gauge against current with bundle derating, voltage drop, pin ratings, terminal and seal compatibility, shield termination.
- **Package data.** Connector face views from the mating side, splice and marker lists, a continuity and insulation test netlist, and the IPC/WHMA-A-620 class [unverified: current edition]. MFG combines them with MEC's 1:1 formboard.
- **Exchange.** VEC 2.2.0 is VDA 4968 and prostep ivip PSI21, and VEC 1.1.2 absorbed KBL 2.4 features [22]. ECO's codec reads and writes VEC in phase 4, and KBL reading follows in phase 5 [unverified: current KBL version].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Harness connectivity | Harness Network joined to board ports | Pin mismatch is a compile error | ELX-O-HAR-1 | 4 |
| Wire table and lengths | Per-variant table from the Network and MEC routes | A missing route makes the length `Undecided`, never 0 | ELX-O-HAR-1 | 4 |
| Gauge, drop and termination checks | Current from simulation or declared loads | Violation names the required gauge or terminal | ELX-O-HAR-1 | 4 |
| Harness package data | Face views, test netlist, terminal data and workmanship class for MFG's package | Missing terminal data listed | ELX-O-HAR-1 | 4 |
| VEC and KBL | VEC 2.2.0 read and write; KBL read | Unmapped elements listed | ELX-O-HAR-2 | 4 (VEC), 5 (KBL) |

## Robotics

Robots are Assemblies with MEC's joints and multibody dynamics. ELX attaches actuators, sensors and transmissions to joints, and inertial properties come from Bodies and Materials, never typed by hand.

| Format | Contents | Notes |
| --- | --- | --- |
| URDF | Links, joints, inertials, meshes, transmissions, ros2_control tags | Tree only; closed loops are cut and the cut is reported |
| SDFormat | Worlds, models, sensors, closed loops | 1.12 [unverified: latest version] |
| MJCF | Bodies, joints, actuators, tendons, sensors, contact | MuJoCo is Apache-2.0 [24]; sdformat_mjcf converts from SDFormat [25] |
| USD | Visual and physics schemas | Through an `io/` writer; gz-usd converts SDF [25] |

Collision geometry comes from `anvil::convex_decompose` with a stated Hausdorff bound, and exports carry their Change id. Kilted Kaiju is supported until November 2026, and the May 2026 ROS 2 release is Lyrical Luth [23]; Crucible generates colcon-buildable packages for the current LTS distribution [unverified: which]. MuJoCo and Gazebo run as External Ops, and CI loads every export in both.

A planning hook sends the model and collision Bodies to an external planner such as MoveIt and receives trajectories as `Field<(Instances, Time), Transform>`, along which torque, current and temperature are checked. Sending a robot program is the `send_robot_program` Act, and Crucible never starts motion (contract section 7.6).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kinematic chain view | Assembly with MEC joints to links, joints and attached models | A joint lacking limits or an actuator where an export needs one is reported | ELX-O-ROB-1 | 4 |
| URDF, SDFormat and MJCF export | Chain to files with stated mesh error | A cut closed loop is reported | ELX-O-ROB-1 | 4 |
| USD export | Chain to USD physics schemas | Unmapped elements listed | ELX-O-ROB-1 | 5 |
| ROS 2 description package | Chain to a colcon-buildable package | A failed build is reported with its log | ELX-O-ROB-1 | 4 |
| Planning hooks | Model and collision world out, trajectory Field back | Planner failure returned as a typed error with its message | ELX-O-ROB-2 | 5 |
| Trajectory checks | Trajectory to torque, current and temperature checks | Exceedance fails with time and joint | ELX-O-ROB-2 | 4 |

## RF: antennas and matching networks

Antennas are Bodies: board copper, stamped metal, flex or coatings on the enclosure. `std::electronics::rf` provides patch, inverted-F, PIFA, monopole, dipole, loop, helix, slot and array features returning Bodies and ports, and board antennas are layout items under DRC.

Flux owns the solvers (D-FLX-32): resonant antennas use frequency-domain Nédélec FEM with port eigenmodes, PML and a fast sweep, and broadband problems use FDTD (R1-22). Palace (Apache-2.0) is the implementation to beat [33], and openEMS, GPL-3.0 [32], is an external cross-check. Antennas are analysed in their housing, a Material without frequency-dependent data is an error, and specific absorption rate is screening only.

Matching synthesis builds L, Pi, T and multi-section networks, using real-frequency methods for broadband problems and reporting the Bode-Fano limit. Values snap to purchasable parts with vendor S-parameter models, Monte Carlo gives return-loss yield, and the result is a Proposal with a layout fragment. Linear RF analysis is phase 4; harmonic balance follows in phase 5.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Antenna features | Ingot features returning Bodies and ports | Geometry outside a feature's range is a typed error | ELX-O-RF-1 | 4 |
| Antenna analysis | Bodies, Materials and ports to `Field<(Ports, Frequency), Complex<Impedance>>`, far-field Fields and efficiency | Under-resolved mesh or missing material data flagged with the fix | ELX-O-RF-1 | 4 |
| Matching synthesis | S-parameters and band to Network edits with yield | An infeasible match reports the Bode-Fano bound | ELX-O-RF-2 | 4 |
| Linear RF analysis | S-parameter network analysis | Non-passive data flagged | ELX-O-RF-2 | 4 |

## System modeling and traceability

### SysML v2

OMG approved SysML v2.0, KerML 1.0 and the Systems Modeling API 1.0 on 21 July 2025 [2], publishing SysML 2.0 in September 2025 [3]. The release repository (EPL-2.0 libraries) was updated in March 2026 for ISO submission [31], and the conformance suite is still in development [2].

**Decision D-ELX-20:** The system model is native Ingot in `std::systems`, whose records mirror SysML v2 part and port definitions, connections, requirements, actions, states, constraints, allocations and variation. SysML v2 is an exchange format through its textual notation and the Systems Modeling API, with a semantic mapping per concept. *Why:* one language keeps one model, three editors, and requirements reference real Parts, nets and checks with checked units. *Rejected:* SysML v2 as a second authoring language, a second source of truth; SysML v1 XMI exchange, which loses semantics. (revised in round 2)

Crucible's own SysML v2 parser and serializer, an `io/` Wasm component, follow the published grammar with the pilot implementation as reference [31]; unmapped concepts survive as opaque annotations.

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
verify(flight_time, by: hover.require(hover.endurance >= flight_time.endurance))
satisfy(flight_time, by: [drone.pack, drone.propulsion])
allocate(functions.power_distribution, to: drone.pdb_board)
```

- **Typed links.** `satisfy`, `verify`, `derive` and `allocate` point at Instances, checks, nets or requirements through `Query`s resolved on every rebuild; a broken link is a `ResolveError`.
- **Computed status.** Status follows from `CheckOutcome`s: verified, failing, undecided, conditional, unverified, outside an envelope, or waived with a reason. Evidence records count only on the same design or a declared compatible one.
- **Computed impact.** A requirement edit re-evaluates only dependent checks, and a Proposal shows status changes beside geometry and metric diffs.
- **Exchange.** ReqIF passes through an `io/` Wasm component, keeping external ids; imported text arrives as `ExternalText`.

### Software and firmware as BOM items

A Software item (contract section 2) records its item number, version, binary hashes, source repository and Change, toolchain, and a software bill of materials in SPDX or CycloneDX [unverified: versions].

1. **Binding.** A `load` relation binds a Software item to a programmable Instance per configuration, and the BOM lists it under the programmed assembly.
2. **Hardware contract.** Crucible generates a board description (pins, peripherals, clocks, memory map) as a Zephyr devicetree overlay or a Rust board-support crate. Firmware declares the description hash it was built against, and a check compares it: "Firmware 1.4.2 expects the status LED on PA5; board revision C routes it to PB3."
3. **Reproducibility.** CI rebuilds firmware in a pinned container as an External Op; a hash mismatch fails the release check.
4. **Release.** A signed release records board revisions, Software item versions and their compatibility matrix.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `std::systems` modeling | Requirements, architecture, functions and allocations as Ingot records | Broken links are `ResolveError`s | ELX-O-SYS-1 | 3 |
| Computed requirement status | Status from check outcomes and Evidence records | Evidence on an incompatible version excluded, with the reason | ELX-O-SYS-1 | 3 |
| SysML v2 exchange | Textual notation and API to and from `std::systems` | Unmapped concepts kept as annotations | ELX-O-SYS-2 | 4 |
| ReqIF exchange | Requirements with external ids | Unmapped attributes kept as annotations | ELX-O-SYS-2 | 4 |
| Software items | Hashes, software bill of materials and `load` bindings | A board-description mismatch fails the release check | ELX-O-SYS-3 | 3 |
| Firmware reproducibility | Pinned-container rebuild and hash comparison | A mismatch fails the release | ELX-O-SYS-3 | 4 |

## State of the art

Commercial tools below (Allegro, Sigrity, Xpedition, HyperLynx, E3.series, Ansys, JMAG, MATLAB) are named from general knowledge; their documentation was not opened, so no claim about their internals is made [unverified]. Every figure is a target.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Connectivity capture | Drawn schematics with ERC (KiCad 10 [1]); code capture with part picking (atopile [4]) | Altium, KiCad 10, atopile | Code as source with a checked drawing (D-ELX-1) | 100% of net-merging branch pairs reported as conflicts; 100% of non-overlapping pairs merged clean; ERC recall 100% |
| Land patterns | Tolerance-driven IPC-7351B patterns [55] | KiCad, over 78% generated from data [1] | 100% generated for standard packages | 2,000 packages against an independent calculation, ±1 µm |
| Automatic placement | Analytical placement with net-crossing and orientation relaxation (Cypress [5]) | Cypress [6]; Allegro X AI [40]; Quilter [41] | Cypress plus height, thermal, decoupling and critical-net terms | Cypress open suite: match published results |
| Interactive routing | Push and shove with walkaround and spring-back (KiCad [45]) | KiCad 10, Allegro, Xpedition | Same structure on exact geometry with delay-aware costs | Replayed sessions: 16 ms per update with 50 shoved items |
| Autorouting | Negotiated congestion with gridless detail; learned routers trail (PCBWorld [30]) | Freerouting [35] | Search-based Wasm router (D-ELX-10) | PCBWorld-Bench: higher completion and fewer vias than Freerouting |
| DRC | Incremental, indexed, exact predicates | Altium, Allegro, KiCad | Tiled integer DRC on `anvil-planar` | 10 s full and 50 ms incremental; zero disagreements with a rational reference |
| Delay tuning | Time-domain constraints with per-layer profiles (KiCad 10 [1]) | KiCad 10, Allegro | Field-solved delay with tolerance propagation | Measured TDR delay on GP5 coupons, ±2% |
| Cross-section RLGC | 2D quasi-static solution with roughness and causal dielectrics | Polar Si9000, HyperLynx | Flux 2D solve cached per cross-section | Conformal-mapping solutions and measured coupons, ±3% on Z0 |
| S-parameter macromodels | Vector fitting with passivity enforcement [52] | SINTEF toolbox [52] | Rust fitting, Hamiltonian check, residue perturbation | 100% passive; fit error at most the toolbox's on the same data |
| Channel simulation | Statistical eye and bit-by-bit with IBIS-AMI [20][21] | Sigrity, HyperLynx | Both modes; AMI as External Ops | IEEE 802.3 reference channels [unverified]; eye height within 5% of a commercial tool |
| PDN impedance | Plane-pair cavity models with via coupling; full wave above their limit | Sigrity PowerSI, HyperLynx PI | Layered sheets in Flux | Analytic resonances ±2%; VNA on GP5 ±15% |
| IR drop and board thermal | DC conduction with thermal coupling; layered board conduction | Sigrity PowerDC | Thin sheets with monolithic electro-thermal Newton; D-ELX-26 | Analytic ±1%; four-wire ±5%; GP5 thermocouples ±5 K |
| Antennas | Nédélec FEM with wave ports and fast sweep [33] | Palace [33]; openEMS [32] | Flux frequency-domain solver (D-FLX-32) | Hallén dipole and cavity patch; resonance within ±1% of Palace |
| Analog simulation | Modified nodal analysis, homotopy, block-triangular LU | VACASK [9]; ngspice for compatibility [7] | Rust engine plus ngspice for vendor models (D-ELX-13, D-ELX-25) | Vendor-model corpus 95%; C6288 within 1.2× of VACASK |
| Compact models | Verilog-A compiled to OSDI (OpenVAF [10]) | OpenVAF with ngspice or VACASK | Own front end to the kernel IR (D-ELX-14) | BSIM4, PSP and VBIC curves, relative 10⁻⁶ |
| Reliability prediction | FIDES 2022 physics-informed models [59] | Tools covering SR-332 and FIDES [58] | Four handbooks plus physics of failure | Worked examples to printed precision |
| Electric machines | Transient FEM with motion and loss models | Ansys, JMAG; Pyleecan with FEMM [44] | Flux maps plus transient `SignOff` (D-ELX-16) | TEAM problems [unverified]; GP6 dynamometer, ±5 points efficiency |
| Magnetics core loss | MagNet data-driven models [39]; iGSE | OpenMagnetics MKF [53] | iGSE plus MagNet-trained models | MagNet metric no worse than the published winners |
| Battery cells | SPMe and DFN with SUNDIALS solvers | PyBaMM [42][43] | Native ECM and SPMe; DFN through Flux (D-ELX-19) | 1 mV RMS against PyBaMM on 1C discharge |
| Control design | Riccati, structured H∞, conic MPC | MATLAB Control System Toolbox | Rust on `linalg`; MPC through Clarabel [49] | Closed-form cases, relative 10⁻⁹; Maros-Meszaros set [unverified] |
| Firmware-in-the-loop | Instruction-level emulation with peripheral models | Renode [28]; QEMU | Renode in lock-step (D-ELX-18) | Identical traces in 100% of repeated runs |
| Harness data | VEC 2.2.0 [22] | Zuken E3.series, Capital | Harness Network with VEC exchange | Zero dropped elements in round trips |
| Robot descriptions | URDF, SDFormat and MJCF with converters [24][25] | Hand-written descriptions; CAD exporters | Generated from the Assembly | Mass properties to relative 10⁻⁹; clean loads in MuJoCo and Gazebo |
| System modeling | SysML v2 with KerML and the API [2][3][31] | Pilot implementation [31] | Native `std::systems` (D-ELX-20) | Pilot examples round trip; OMG suite when published |
| Matching networks | Real-frequency matching; Bode-Fano bound | RF circuit tools [unverified] | Synthesis with real parts and yield | Analytic L-networks to 10⁻⁶; bound never exceeded |

## Platform notes

- **Integer board data.** Layout, DRC, fills and the board model hash identically on every Tier 1 platform, browsers included, which is stronger than the class rule. Chord points come from `detmath`, never a platform libm, and fabrication text uses bundled fonts rendered by Crucible.
- **External Ops.** IBIS-AMI models, native FMUs, emulators, Verilator, ngspice, vendor engines, robot simulators and firmware toolchains run only on Linux untrusted-evaluation workers. Every client reaches them remotely, and air-gapped installs need a local Linux worker (contract section 9). Vendors often ship AMI and FMU binaries for x86-64 Windows and Linux only [unverified], so results carry the worker's class.
- **Emulator and simulator packages.** Renode publishes packages for Linux, macOS on Apple silicon and Windows [28], with ARM64 status [unverified]; MuJoCo's prebuilt binaries cover Linux on x86-64 and AArch64, Windows on x86-64, and macOS [24].
- **`f64` paths.** Analog analyses need `f64`, which Metal and WebGPU lack, so they run on CPU SIMD lanes everywhere; a server GPU class with Vulkan `SHADER_F64` may batch Monte Carlo at `Interactive` (contract section 7.5).
- **Browser memory.** Under PLT's browser memory table, DRC, fills and analyses estimated above 512 MiB run in the disposable heavy worker, and larger boards go remote.
- **GPU placement.** The placer's FFT and gradient kernels go through `crucible:ops/flux` with registered CPU paths; placement is an edit, so cross-class differences never change an evaluation.
- **Tablets and phones.** iPadOS and Android tablets view, review and make light edits, with heavy analyses remote; no Act is approvable on a phone (contract section 7.6).
- **Hardware access.** Bench adapters and flashing use USB and serial through `apps/platform`; browsers use WebUSB and WebSerial where available [unverified: Safari and Firefox], and a local adapter program connects to `api` elsewhere.
- **Accessibility.** Schematics, netlists, rules and DRC results are navigable trees through AccessKit, and a screen-reader user can capture and review a whole design as code.

## Interfaces with other subsystems

| To | ELX provides | Types |
| --- | --- | --- |
| ING | Builder semantics for `network { … }`; data modules for `Schematic` and `Layout`; `#[configuration]` and `Tol` correlation-group use | `Network`, `Feature` |
| FLX | The `network { … }` builder, port types and element libraries, the Verilog-A front end, board excitations and layered-sheet geometry | `Network`, `Field` |
| ANV | Planar workloads for `anvil-planar`; bend lines for `anvil::fold` | `Body` |
| KLN and `repo` | Net partitions for the connectivity merge condition; `bare_board_invariant`; Software items and `load` bindings; lifecycle placeholders | `Network`, `Part` |
| MEC | Bare and assembled boards (flat and folded), connector `CoordSys` values, harness connectivity and wire data, lumped motor and drive elements | `Part`, `Assembly`, `Network` |
| MFG | The board model (layers, stackup, classes, netlist, footprints, placements, `test_point` features, rules); the DRC engine that runs MFG's rule packs; harness connectivity, wire tables and package data; DFM findings shown on board objects | `Part`, `Network` |
| COV | Electrical use of physics models; equivalent-circuit and SPMe cells, swelling and stack pressure, and abuse mechanics (13.4); packs | `Material`, `Field` |
| UIX | Canvas buffers for schematic, layout and constraint views; router and placement on the edit lane; rule declarations; `schematic_matches_network`; recorded routing and placement sessions for UIX-O-ELX-1 | `crucible:ui/canvas2d` buffers |
| AGT | Std features with doc metadata; electronics checks for GP5; Proposals from placement, routing, matching and decoupling tools; datasheet extraction tasks | `CheckOutcome`, Proposal |
| ECO | The board, netlist and library models; the electrical semantics of IDX, IPC-2581, ODB++, KiCad, harness, robot and systems formats; `CatalogSelection`; SysML v2 and ReqIF mappings | `Network`, `Part` |

| From | ELX requires |
| --- | --- |
| ING | `network { … }` builder blocks with set-like accumulation; power expressions checked by the type checker; `#[configuration]`; `#[interface]` records; `Tol` correlation groups; `CatalogSelection` re-resolution; `#[waive]`; data modules with one item per line |
| ANV | `anvil::planar::boolean`, `offset`, `distance` and `medial_axis` with conservative snapping; `anvil::fold`; `anvil::convex_decompose` |
| FLX | `compile_network` and `solve_dae`; block-triangular LU in `linalg`; layered sheets and quasi-static, magnetostatic, eddy-current and full-wave solvers; conjugate heat transfer; parameter-domain forms; multibody plants and their linearization; `fft_solve` through `crucible:ops/flux`; the FMI and SSP runtime; Verilog-A constructs in the kernel IR |
| KLN and `repo` | The connectivity merge condition matched by provenance; option semantics and the 150% BOM; `Purchased` Items and the parts policy; definition digests with late-bound placeholders; untrusted-evaluation workers for External Ops; the hardware runner for rig tests |
| MEC | Enclosure geometry, keep-ins and connector frames; joints, mates and gear records for plants and drivetrain Networks; harness routes, bundle geometry, lengths and formboard geometry; fastener selection under the parts policy |
| MFG | Fabricator and assembler rule packs per class; output packages, panelization, stencils and test programs; DFX feedback; the harness manufacturing package |
| COV | Dielectric, copper, magnetic and cell Materials with envelopes; physics models for EMC, thermal and cells; precision classes (D-COV-23) |
| UIX | The Electronics preset and its keymap presets; schematic, layout and constraint-manager canvases on `crucible:ui/canvas2d` (D-UIX-27); the edit-lane client; chart viewers for waveform, Bode, Smith and eye charts with time scrubbing; UIX-O-ELX-1 replaying ELX's recorded sessions |
| AGT | Datasheet extraction with page references and labels; Proposals under a `Budget` for long tool runs |
| ECO | Catalog service, definition packages, `parts::` publishing and the offer schema; offer connectors; every `io/` reader and writer with its phase, including STEP part bodies (phase 1), IDF and STEP boards (phase 2), IDX, IPC-2581C, Gerber, ODB++, VEC, KiCad, EAGLE and the KiCad-based migration path |
| PLT | `detmath`; `linalg` for circuit LU; browser memory table; USB and serial access in `apps/platform` |

ECO's format catalog owns versions, exchange levels and phases. ELX's formats are IDX V6 [14], IPC-2581C [19], Touchstone 2.1 and IBIS 8.0 [20][21], VEC 2.2.0 [22], SysML v2 [31] and ReqIF. They also include Specctra DSN and SES, URDF, SDFormat and MJCF [24][25], KiCad files, SPICE netlists and Verilog-A. KiCad's IPC API (Protocol Buffers over NNG [64]) serves as a live bridge for teams keeping some boards in KiCad during migration.

## Oracles

ELX oracles live in `oracles/elx/`; held-out sets are never shown to agents, and loosening a tolerance needs human approval.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ELX-O-EXT-1 | Port types, element libraries and analyses defined in a user namespace | Compile and evaluate identically to their std equivalents |
| ELX-O-NET-1 | Network builder and hierarchy | Connect order never changes the net partition; hierarchical golden designs flatten to known netlists |
| ELX-O-NET-2 | Net ties and connectivity merges | 100% of seeded net-merging branch pairs reported as `Conflict::NetMerge`; 100% of non-overlapping pairs merge clean; every untied named-net join fails |
| ELX-O-NET-3 | Port types and element stamps | Every std port's power expression type-checks and seeded wrong ones fail; RLC, motor and drivetrain cases match analytic solutions |
| ELX-O-VAR-1 | Variants | Covering set built; symbolic BOM equals brute force on small products; a seeded footprint-changing variant fails `bare_board_invariant` |
| ELX-O-SCH-1 | Drawn schematics | In 10⁵ random view and code edits, view edits never change connectivity and no drawn group spans two nets after any code edit |
| ELX-O-SCH-2 | ERC | 100% recall on 300 human-labelled seeded schematics and a held-out 100; zero false positives on clean designs |
| ELX-O-SCH-3 | Netlists, schematic import and migration | Re-import equality; migrated designs' netlists equal the source tool's own netlist export |
| ELX-O-SCH-4 | Drawing output | Visual regression against stored references; placeholders filled only at output |
| ELX-O-CAT-1 | Facets, symbols and consistency checks | Every seeded inconsistent record blocked with the right `CatalogError` |
| ELX-O-CAT-2 | Footprint generators | Pad geometry within ±1 µm of an independent calculation on 2,000 packages |
| ELX-O-CAT-3 | Selections and offers | Identical pins give identical parts on every platform; an argument change re-resolves; an update's diff lists every substitution |
| ELX-O-CAT-4 | Parts policy | A non-approved part fails the policy check unless a waiver names it; a new-part Proposal creates all its records |
| ELX-O-CAT-5 | Datasheet extraction | Agreement with hand-entered held-out records; every value cites a page |
| ELX-O-BRD-1 | Stackups, classes and board Bodies | Fabricator capability replay; rasterized copper equals layout data within the chord bound |
| ELX-O-BRD-2 | Enclosure co-design | Scripted GP5 enclosure changes update placements or fail with `ResolveError` |
| ELX-O-BRD-3 | IDX exchange | IDX baselines and scripted change scenarios; proposals conflicting with locks rejected item by item |
| ELX-O-BRD-4 | Folding and flex strain | Folded geometry equals analytic cylinder maps; strain matches thin-beam bending and a 3D FEM cross-check |
| ELX-O-BRD-5 | Lifecycle placeholders | Assigning a revision or an engine upgrade with bit-level changes only flips zero boards to modified |
| ELX-O-LAY-1 | DRC | Seeded violations at random positions all found by comparison with a slow exact-rational checker; rotated, mirrored and translated boards give identical violation sets |
| ELX-O-LAY-2 | Fills and teardrops | Idempotent and tile-order independent; every derived fill passes the exact checker with zero tolerance |
| ELX-O-LAY-3 | Interactive placement and routing | Recorded sessions replay byte for byte; DRC clean after every finished route; 16 ms per update with 50 shoved items (target) |
| ELX-O-LAY-4 | Autorouting | PCBWorld-Bench metrics [30] against Freerouting [35]; no Proposal with DRC errors |
| ELX-O-LAY-5 | Automatic placement | Cypress open suite [5] and held-out boards; targets in State of the art |
| ELX-O-LAY-6 | Rules and isolation barriers | Precedence property tests; worked examples from each supported safety standard reproduced |
| ELX-O-LAY-7 | Test points | Coverage recomputed from the netlist; every net without access receives a proposed test point or a stated reason |
| ELX-O-SI-1 | Impedance, RLGC, extraction and delay | ±1% against conformal-mapping solutions; ±10% against measured GP5 coupons (target) |
| ELX-O-SI-2 | Macromodels | Fit error under the stated bound; passive after enforcement by an independent Hamiltonian check |
| ELX-O-SI-3 | IBIS and channels | IBISCHK8 parse agreement [20]; vendor AMI examples reproduced |
| ELX-O-PI-1 | PDN, decoupling and IR drop | Analytic cavity resonances ±2%; analytic strip and annulus resistances ±1%; exact optimum on small decoupling instances |
| ELX-O-PI-2 | Electro-thermal coupling | Analytic self-heating of a uniform strip; `Runaway` reported at the turning point under current drive |
| ELX-O-EMC-1 | EMC screening | Analytic small-loop and short-dipole radiation; seeded rule and coupling cases; GP6 chamber scans as screening references |
| ELX-O-TH-1 | Board thermal | Layered model within its stated bound of explicit 3D copper on zoom cases; GP5 thermocouples ±5 K (target) |
| ELX-O-SIM-1 | Analog analyses | ngspice regression corpus run as an External Op and textbook circuits, relative 10⁻³ or absolute 1 µV |
| ELX-O-SIM-2 | Vendor models | At least 95% of the unencrypted vendor corpus parses, converges and matches the vendor's reference engine within 1% (target) |
| ELX-O-SIM-3 | Verilog-A compact models | I-V and C-V curves against OpenVAF-compiled references run as External Ops, relative 10⁻⁶ |
| ELX-O-SIM-4 | Monte Carlo, sensitivity and worst case | Identical samples in every class; added samples leave earlier ones unchanged; adjoint sensitivities pass Taylor tests |
| ELX-O-SIM-5 | Mixed-signal | Event times within one analog step of ngspice XSPICE references |
| ELX-O-REL-1 | Reliability and derating | Handbook worked examples to printed precision [58][59]; physics-of-failure models against their cited datasets |
| ELX-O-MCH-1 | Machines | Analytic slotless fields and winding factors, torque ±3%; GP6 dynamometer efficiency ±5 points (target) |
| ELX-O-MCH-2 | Actuators, sensors and drives | Analytic solenoid force; datasheet transfer curves; averaged-model cases against ngspice |
| ELX-O-CTL-1 | Control design and code generation | Closed-form Riccati, margin and reduction-bound cases to relative 10⁻⁹; generated code bit-exact with the Ingot reference |
| ELX-O-CTL-2 | FMU elements and bus simulation | Reference FMUs map ports and units correctly; FMI-LS-BUS reference examples [unverified: availability] |
| ELX-O-FW-1 | Firmware-in-the-loop | Reference firmware traces identical across repeated runs per class; PWM-to-RC timing error within the reported bound |
| ELX-O-FW-2 | Hardware-in-the-loop | Fixed-step exports bit-exact with the reference; evidence on an incompatible version never counts |
| ELX-O-BAT-1 | Cell models | 1 mV RMS against PyBaMM on shared parameter sets (target); analytic diffusion; fitted parameters recover known values |
| ELX-O-BAT-2 | Packs and swelling | Hand-computed pack resistance and capacity; analytic busbar resistance; GP6 pack voltage under 30 mV RMS per cell (target) |
| ELX-O-BAT-3 | Pack safety and abuse | Published coordination examples; abuse screening against cited test data, labelled screening |
| ELX-O-PWR-1 | Converters | Textbook steady-state and averaged-model cases; analytic loop inductance; GP6 calorimetric efficiency |
| ELX-O-PWR-2 | Magnetics | MagNet metric no worse than the iGSE baseline [39]; Dowell analytic cases |
| ELX-O-HAR-1 | Harness | Hand-checked golden harness wire table, lengths and checks; package contents complete |
| ELX-O-HAR-2 | VEC and KBL | Schema validation and round trip with zero dropped elements |
| ELX-O-ROB-1 | Robot exports | Mass properties equal Anvil's to relative 10⁻⁹; files load in MuJoCo and Gazebo without warnings; sdformat_mjcf round trip [25] |
| ELX-O-ROB-2 | Trajectories and planning hooks | Analytic single-joint cases; recorded planner sessions |
| ELX-O-RF-1 | Antennas | Dipole impedance against Hallén's integral equation for the modelled radius; cavity-model patch; Palace cross-check, ±2% resonance |
| ELX-O-RF-2 | Matching and linear RF | Analytic L-networks to 10⁻⁶; Bode-Fano bound never exceeded; textbook amplifier cases |
| ELX-O-SYS-1 | System model and status | Resolution tests; seeded status corpus |
| ELX-O-SYS-2 | SysML v2 and ReqIF | Round trip of the pilot implementation's examples [31] and sample ReqIF files with no dropped elements |
| ELX-O-SYS-3 | Software items | Seeded board-description mismatches all fail; reference firmware rebuilds to identical hashes |
| ELX-O-DET-1 | Determinism and label invariance | Golden boards hash identically on every Tier 1 platform; re-randomized names and designators leave copper and check values identical |

## Phasing

Capabilities that several tabs phase (conjugate heat transfer, electro-thermal coupling, FMU export and SSP, and every battery cell row) take their phase from contract section 13.4.

| Phase | ELX contribution to the gate |
| --- | --- |
| 0 | None; ELX has no team (contract section 13.2) |
| 1 | No gate contribution. The two-person research track prototypes the modified-nodal-analysis engine, assembles the vendor-model corpus and settles the Verilog-A front end's scope |
| 2 | GP3: the `network { … }` builder, rotational, translational and thermal port libraries, and drivetrain elements from MEC's gear records. Also ECO's IDF, STEP board and IDX baseline import, on an early 1.x train, for enclosure design |
| 3 | GP5, its board fabricated and assembled from Crucible outputs alone: schematic, ERC, catalog parts and policy, footprints, stackup and classes, layout, DRC, fills, through, blind and buried vias, routing, delay tuning, test points, enclosure co-design, impedance, IR drop, board thermal, simulation with Monte Carlo and vendor models, variants, Software items and requirements. Evidence: DRC and ERC clean; MFG's fabricator DFM with zero errors; coupon impedance within ±10% and hottest part within ±5 K of measurement (targets); board data identical on every Tier 1 platform |
| 4 | GP6: machines and drives, equivalent-circuit and SPMe cells, packs and swelling, converters and magnetics, electro-thermal coupling, controls, FMU elements, firmware-in-the-loop, HIL evidence, antennas, SI channels, PDN, EMC screening, HDI, rigid-flex, harness and VEC exchange, robot exports, reliability, SysML v2, placer and autorouter, IDX change proposals. Evidence (targets): hover endurance ±10% of flight test; motor efficiency ±5 points; pack voltage under 30 mV RMS per cell; attitude-loop overshoot and settling ±20%; antenna resonance ±2% |
| 5 | GP7: the MEMS reduced-order model as a Network element for readout simulation. Also DFN cells (FLX), degradation, periodic steady state and harmonic balance, H∞ and MPC, FMI-LS-BUS, USD, immunity screening, RTL co-simulation, KBL import, planning hooks |
| 6 | GP11 CubeSat: board, harness and firmware flows. GP12 EV battery sub-pack with BMS, harness and charger: pack safety screening, abuse mechanics, pack-scale DFN, high-voltage isolation barriers |
| 7 | None |

## Open questions

1. **ODB++ terms.** R4-27 settles the plan: ECO builds an ODB++ writer in phase 3, and MFG offers it as a package. Siemens' page says ODB++ interfaces cost nothing and lists a partner program, but states no licence for third-party writers [18]; ECO confirms the terms before the writer ships.
2. **IPC-2581 revision.** Revision C dates from December 2020 [19], and the consortium's site names no revision [69]; a later revision is [unverified].
3. **Land-pattern document.** IPC's catalog pages for IPC-7351 and IPC-7352 could not be opened, so which document now applies is [unverified] (R4-42). The pinned standard package keeps either answer an explicit update.
4. **Licensed tables.** FIDES guides need registration [59]; SR-332, MIL-HDBK-217, the safety standards behind D-ELX-24 and the IPC class rule packs carry their own terms. Which tables may ship in std, and which stay user-licensed packages?
5. **Verilog-A front end.** The phase 1 research track decides whether a clean-room front end fits phase 3; the fallback is ported SPICE3 models plus vendor models in ngspice.
6. **Vendor engines.** LTspice and PSpice terms for batch use in containers are [unverified]; D-ELX-25 offers them only where those terms allow.
7. **Battery reference models.** The hysteresis, swelling and abuse rows need published models with test data before their phases; none was opened this round.
8. **Renode.** Determinism under multi-core and network models, and ARM64 hosts, need verification [28][62].
9. **Learned cost hints and patents.** PCBWorld does not state its corpus licence [30], and placement and routing are an active patent area; a freedom-to-operate review precedes the placer and autorouter.
10. **Data-module size.** `Schematic` and `Layout` are Ingot data modules; if very large layouts parse too slowly, ING's binary sidecar keeps their semantics and changes only the file format.
11. **ROS 2 target.** The LTS distribution to target needs confirmation from the release schedule [23].
12. **Findings declined in part.** R1-39's CUDA and ROCm route waits for the phase 4 gate decision in contract section 7.5; Vulkan `SHADER_F64` server classes serve until then.
13. **Firmware flashing outside `unattended_safe` rigs (round 3 contract request).** Contract section 7.6 names no Act for flashing a board on a bench without that policy, so a person flashes it there. Round 3 decides whether flashing becomes a physical-effect Act with an Approval over the image digest or stays manual.

## Contract change requests

- CCR-ELX-8, battery swelling and abuse rows: accepted in contract v5; contract section 13.4 holds both rows.

## Sources

Pages opened with WebFetch in October 2026; [65] to [69] were opened in round 2. Vendor performance claims are reported as the vendors state them.

- [1] KiCad project, "Version 10.0.0 Released", 20 March 2026. https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/
- [2] Object Management Group, press release on SysML v2.0, KerML 1.0 and Systems Modeling API and Services 1.0, 21 July 2025. https://www.omg.org/news/releases/pr2025/07-21-25.htm
- [3] Object Management Group, SysML specification page. https://www.omg.org/spec/SysML
- [4] atopile repository (MIT). https://github.com/atopile/atopile
- [5] Cypress: VLSI-inspired PCB placement with GPU acceleration, ISPD 2025 paper. https://www.csl.cornell.edu/~zhiruz/pdfs/cypress-ispd2025.pdf
- [6] NVlabs Cypress repository (Apache-2.0). https://github.com/NVlabs/Cypress
- [7] ngspice project home page. https://ngspice.sourceforge.io/
- [8] Debian copyright file for ngspice 47. https://tracker.debian.org/media/packages/n/ngspice/copyright-47ds-1
- [9] VACASK repository (AGPL-3.0) with benchmark tables. https://codeberg.org/arpadbuermen/VACASK
- [10] OpenVAF repository (GPL-3.0). https://github.com/pascalkuthe/OpenVAF
- [11] SSP standard home page. https://ssp-standard.org/
- [12] FMI project, "FMI 2.0.5 and FMI 3.0.2 released". https://fmi-standard.org/news/2024-11-27-fmi-2.0.5-and-3.0.2
- [13] SSP project, "SSP 2.0 release". https://ssp-standard.org/news/2024-12-20-ssp-2-0-release/
- [14] prostep ivip, ECAD/MCAD Collaboration Implementor Forum. https://www.prostep.org/en/projects/ecad/mcad-collaboration-implementor-forum
- [15] Ucamco, Gerber format downloads (Layer Format revision 2026.05, Job Format 2020.08, XNC 2021.11). https://www.ucamco.com/en/gerber/downloads
- [16] I-Connect007, "Ucamco releases final version of the Gerber X3 specification", 2020. https://iconnect007.com/index.php/article/122204/ucamco-releases-final-version-of-the-gerber-x3-specification/122207?skin=pcb
- [17] Wikipedia, "Gerber format". https://en.wikipedia.org/wiki/Gerber_format
- [18] Siemens, ODB++ product page. https://www.siemens.com/en-us/products/pcb/odb-plus-plus/
- [19] IPC, "IPC releases IPC-2581 Revision C", 1 December 2020. https://www.electronics.org/news-release/ipc-releases-ipc-2581-revision-c-generic-requirements-printed-board-assembly-products
- [20] IBIS Open Forum home page (IBIS 8.0, Touchstone 2.1, IBIS-ISS 1.0). https://ibis.org/
- [21] IBIS Open Forum, IBIS 8.0 page (ratified 5 December 2025). https://ibis.org/ver8.0/
- [22] prostep ivip ECAD wiki, VEC specifications. https://ecad-wiki.prostep.org/specifications/vec/
- [23] Open Robotics, "ROS 2 Kilted Kaiju Released", 23 May 2025. https://www.openrobotics.org/blog/2025/5/23/ros-2-kilted-kaiju-released
- [24] MuJoCo repository (Apache-2.0). https://github.com/google-deepmind/mujoco
- [25] SDFormat, "Interoperability with other modeling formats". https://sdformat.org/tutorials/developers/interoperability_formats/
- [26] FMI project, "Release of FMI-LS-BUS v1.0". https://fmi-standard.org/news/2025-07-21-fmi-ls-bus-v1.0-release/
- [27] FMI project, news listing for 2025 and 2026. https://fmi-standard.org/news/
- [28] Renode repository (MIT). https://github.com/renode/renode
- [29] Verilator repository (LGPL-3.0 or Artistic-2.0). https://github.com/verilator/verilator
- [30] PCBWorld: a benchmark environment for engine-grounded PCB design automation, arXiv 2607.05915. https://arxiv.org/abs/2607.05915
- [31] OMG Systems Modeling community, SysML v2 release repository. https://github.com/systems-modeling/sysml-v2-release
- [32] openEMS documentation, introduction. https://docs.openems.de/intro.html
- [33] Palace repository (Apache-2.0). https://github.com/awslabs/palace
- [35] Freerouting repository (GPL-3.0). https://github.com/freerouting/freerouting
- [39] Chen, Sullivan et al., "MagNet Challenge for Data-Driven Power Magnetics Modeling", IEEE Open Journal of Power Electronics 6 (2025), record page. https://collaborate.princeton.edu/en/publications/magnet-challenge-for-data-driven-power-magnetics-modeling/
- [40] Cadence, "Cadence Introduces Allegro X AI", Business Wire, 6 April 2023. https://www.businesswire.com/news/home/20230406005098/en/Cadence-Introduces-Allegro-X-AI-Accelerating-PCB-Design-with-More-Than-10X-Reduction-in-Turnaround-Time
- [41] Quilter, "About". https://www.quilter.ai/about
- [42] PyBaMM repository (BSD-3-Clause). https://github.com/pybamm-team/PyBaMM
- [43] PyBaMM documentation, public API. https://docs.pybamm.org/en/stable/source/user_guide/fundamentals/public_api.html
- [44] Pyleecan repository (Apache-2.0). https://github.com/Eomys/pyleecan
- [45] KiCad source documentation, `PNS::SHOVE` class reference. https://docs.kicad.org/doxygen/classPNS_1_1SHOVE.html
- [47] Clipper2 repository (BSL-1.0). https://github.com/AngusJohnson/Clipper2
- [48] faer documentation, sparse linear algebra module (MIT). https://docs.rs/faer/latest/faer/sparse/linalg/index.html
- [49] Clarabel.rs repository (Apache-2.0). https://github.com/oxfordcontrol/Clarabel.rs
- [50] Rumoca repository (Apache-2.0). https://github.com/CogniPilot/rumoca
- [51] ModelingToolkit.jl repository. https://github.com/SciML/ModelingToolkit.jl
- [52] SINTEF, Vector Fitting software page. https://www.sintef.no/en/software/vector-fitting/
- [53] OpenMagnetics MKF repository (MIT). https://github.com/OpenMagnetics/MKF
- [54] Altium, "Defining Design Requirements Using the Constraint Manager". https://altium.com/jp/documentation/node/322309/printable/print
- [55] Electronic Specifier, "IPC releases new revision of surface mount design and land pattern standard", 23 July 2010. https://www.electronicspecifier.com/?p=119981
- [56] GlobalSpec standards record for IPC-7351. https://standards.globalspec.com/std/1267508/ipc-7351
- [57] Autodesk Fusion blog, "Why ECAD MCAD Integration Just Makes Sense", 3 July 2025. https://www.autodesk.com/products/fusion-360/blog/why-ecad-mcad-makes-sense/
- [58] PTC Windchill Risk and Reliability reference guide, prediction model descriptions. https://support.ptc.com/help/wrr/r12.0.4.0/en/wrr/ReferenceGuide/prediction/model_descriptions.html
- [59] FIDES reliability methodology home page. https://www.fides-reliability.org/en
- [60] Xyce repository (GPL-3.0). https://github.com/Xyce/Xyce
- [61] Modelica Standard Library repository (BSD-3-Clause). https://github.com/modelica/ModelicaStandardLibrary
- [62] RISC-V International blog, "CPU RTL co-simulation in Renode". https://riscv.org/blog/cpu-rtl-co-simulation-in-renode/
- [63] Open Source Modelica Consortium, OSMC Public License 1.8. https://openmodelica.org/osmc-pl/osmc-pl-1.8.txt
- [64] KiCad developer documentation, IPC API. https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/
- [65] KiCad project, "Version 9.0.0 Released", 20 February 2025. https://www.kicad.org/blog/2025/02/Version-9.0.0-Released/
- [66] KiCad 9.0 documentation, KiCad project manager (importing non-KiCad projects). https://docs.kicad.org/9.0/en/kicad/kicad.html
- [67] KiCad 9.0 documentation, PCB Editor (fabrication and 3D model exports). https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html
- [68] ngspice project, news and release history. https://ngspice.sourceforge.io/news.html
- [69] IPC-2581 Consortium home page. https://www.ipc2581.com/
