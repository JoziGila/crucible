# Electronics and systems (ELX)

Electrical intent in Crucible is a typed Ingot program: connectivity is a `Network` in code, and a schematic is a drawing proved equal to it. A board is a Part whose copper is integer layout data, and analyses return Fields with error budgets and checks with stated validity envelopes. Schematic, board, enclosure, harness, firmware and requirements share one design repository, so no exchange step can go stale.

## Scope and ownership

ELX owns connectivity, the `network { … }` builder and its element libraries, catalog parts' electrical facets, schematic capture, the board model, layout and design-rule checking (DRC). It also owns electrical, mechatronic, battery and power models, control design, harness connectivity, robot export and requirements traceability, in `std::electronics` and `std::systems`.

| Concern | Owner | What ELX contributes |
| --- | --- | --- |
| Network compilation, the DAE solver, sparse LU in `linalg`, field solvers, plant linearization, the FMI runtime | FLX | Port types, element libraries, the Verilog-A front end |
| Fabrication and assembly packages, panels, stencils, rule packs, test programs | MFG | The board model; the DRC engine that runs MFG's rule packs |
| Harness 3D routing and formboard geometry | MEC | Harness connectivity, wire tables, electrical checks |
| Catalog service, registry, every `io/` reader and writer with its phase, ECAD migration | ECO | The electrical meaning of each format |
| Schematic, layout and constraint canvases; the Electronics preset (D-UIX-27) | UIX | Content drawn through `crucible:ui/canvas2d` |
| Merge driver, variant semantics, 150% BOM, Items and definitions | KLN | Net partitions; `bare_board_invariant`; the variant covering-set policy |
| Act machinery, `edit.stream` and the approval page | AGT | `flash_device` plan contents and board hazards (D-ELX-29) |
| Materials, physics models, validity envelopes | COV | Equivalent-circuit and SPMe cells (contract section 13.4) |

Out of scope, stated plainly:

- Integrated-circuit and FPGA internals; chips enter only as catalog-part models.
- Regulatory verdicts; EMC, safety and radio results are screening evidence for a test lab.
- Real-time execution; hardware-in-the-loop runs outside Kiln.
- Device physics below compact models, arcs in contactors and fuses, and electrochemistry below porous-electrode theory.
- Field-life forecasts; handbooks give comparative failure rates.

Before the phase 1 gate, electronics work is only a circuit-simulation research track (contract section 13.2), so every capability lands in phase 2 or later. New electrical physics enters only through the public mechanisms below (principle 1). An acoustic domain, for example, is a package declaring one port type.

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
| `Schematic` | Drawn topology for one `Network`: symbols, segments, junctions, labels, sheets | Data module of table rows, checked against connectivity (D-ELX-27) |
| `Stackup` | Ordered layers with Materials, `Tol<Length>` thicknesses, via spans and regions | Plain value referencing Materials |
| `Layout` | Placements, tracks, arcs, vias, zones and keep-outs | Integer-coordinate data module (D-ELX-6, D-ELX-27) |
| `Footprint` | Padstacks, mask, paste, silkscreen, courtyard, pad-to-pin map | Integer data; Bodies derived |
| `CatalogSelection` | A parametric pick of a catalog part (D-ELX-3) | Pure function over pinned data |
| Bare and assembled board | The printed board; the board with its parts | A Part of kind `pcb`; an Assembly |
| Design rule | Clearance, width, impedance, delay, creepage | A check from `std::electronics::rules` |
| Responses | Waveforms, spectra, sweeps | `Field<(Ports, Time), Voltage>` and similar |

**Decision D-ELX-1:** Connectivity is Ingot code, and a schematic is a stored drawing that the blocking check `schematic_matches_network` proves equal to it. *Why:* agents and the code editor need text connectivity (principle 2), which merges semantically and type-checks before it runs; atopile shows code capture works [4]. *Rejected:* drawing as the source (KiCad, Altium), whose geometric connectivity merges badly; generated drawings, which lose signal-flow layout; an unchecked drawing (R4-22). (revised in round 2)

**Decision D-ELX-2:** Every use of a catalog part in a network is an Instance of the Part its definition package describes. The bare board is a Part, and the assembled board is an Assembly placed by the footprint placements. *Why:* one derived BOM view covers mechanical and electrical items, and moving a part in layout is the same edit as in the assembly. *Rejected:* a separate symbol-instance concept, which duplicates Instance and needs a sync step.

[[DIAGRAM diagrams/08-electronics-source-model.jsx: electrical source model · what editors write and what Kiln derives]]

Read it left to right: outlined boxes are files that editors write, tinted boxes are what Kiln derives, and the dashed arrow is enclosure geometry.

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

**Decision D-ELX-15:** `Network`, built with `network { … }`, is the lumped model for every physical domain, compiled by Flux into one DAE. *Why:* one mechanism replaces separate circuit, block-diagram and physical-network tools, so a motor drive from inverter to load is one model. *Rejected:* separate formalisms per domain, which need adapters at every boundary; the round 1 type name, which the contract replaced. (revised in round 2)

Electrical, magnetic, thermal, rotational, translational, fluid and signal ports join through the same `connect`. Each port type declares its across and through quantities and its power expression, which the compiler checks is a power (contract section 5). Across variables are equal at a node, through variables sum to zero, and signal ports are causal.

Flux compiles and integrates Networks (D-FLX-27). ELX supplies the element libraries, including drivetrain elements built from MEC's gear records. Each element states its envelope; lumped wiring holds while a line is under a tenth of a wavelength.

### Hierarchy, buses and ports

- **Hierarchy.** A sub-network is a feature returning a `Network`, and repeated channels are loops keyed per contract section 5. It adds an Assembly level only when the designer declares a sub-assembly, such as a daughterboard.
- **Buses.** A bus is a compound `#[interface]` port or a net vector (`Bus<8>`). Joining compound ports checks roles, and an incompatible join is a compile error suggesting an adapter part.
- **Global nets.** None are implicit; a design may declare `global_net("GND")` once at the top level.
- **Electrical typing.** `Power` carries a `Tol<Voltage>` range and pins carry absolute-maximum ranges. Static mismatches fail at compile time; value-dependent ones become checks.

### Net ties and merges

**Decision D-ELX-21:** Two named nets join only through an explicit `tie(net_a, net_b, at: footprint)`, which rule checks, netlists and IPC-2581 export treat as one intended short. *Why:* union semantics would turn two branches attaching one pin to different nets into a silent short (R4-03), yet star grounds need visible shorts (R4-22). *Rejected:* letting union semantics join named nets; net ties as drawing-only symbols, which netlists and DRC cannot see.

A pin that `connect` places in two named nets fails the unwaivable rule `named_net_join`, naming the pin, both nets and both statements. Nets match by the `CallSite` of their `net(…)` call, never by name.

Kiln derives each design's net partition as a node. A merge that unions nets distinct in the base and in each side is `Conflict::NetMerge`, naming the pins, nets and Changes (contract section 7.1). The rule also covers harness Networks and `std::systems` interface connections.

### Variants

**Decision D-ELX-4:** A board's variants are `#[configuration]` record parameters under KLN's option semantics, and CI builds the listed sellable configurations plus a pairwise covering set. *Why:* variants reuse Kiln's caching and checks, and region, feature and assembly options follow one model (R3-18, R4-21). *Rejected:* one `Variant` enum built exhaustively in CI, exponential in the options; variant tables beside the design, a second mechanism with its own merge rules. (revised in round 3)

Fitted state, part choice and values are `if` and `match` expressions on the options. KLN owns variant semantics, the symbolic 150% BOM and its oracle (KLN-O-PLM-5); ELX owns the covering-set policy and the bare-board rule below.

```
#[configuration]
pub struct Options { region: Region, lite: bool }

let r_term = resistor(120ohm ± 1%).fitted(!opts.lite)        // land pattern stays on the bare board
let modem  = match opts.region {
    Region.eu => modem_eu,                                   // both CatalogSelections require
    _         => modem_na,                                   // land_pattern: lga_52
}
```

An unfitted part keeps its land pattern and leaves the assembly BOM and placement data. The check `bare_board_invariant` reuses the 150% BOM's abstract interpretation. Every branch reaching copper, drill, outline, mask or silkscreen must give one `GeometryId`, or the check fails naming the configuration and item.

Copper that truly differs needs a declared fabrication variant with its own bare-board Item, and each variant states paste handling for unfitted parts.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Network builder | `network { … }` returns a `Network`; `connect` is order-independent and idempotent | Type errors at compile time with fixes, such as an adapter part | ELX-O-NET-1 | 2 |
| Domain port types | Across, through and power expression; std ports for every domain in D-ELX-15 | Power expression not a power: compile error | ELX-O-NET-3 | 2 |
| Drivetrain elements | Gear ratio, mesh stiffness, couplings and bearing friction with rotational ports, parameterized from MEC's gear records | A gear record missing a parameter is a typed error naming it | ELX-O-NET-3 | 2 |
| Electrical element library | Modified-nodal-analysis stamps for passive, source, switch and controlled elements, each with an envelope | Element outside its envelope flagged with the variable | ELX-O-NET-3 | 3 |
| Hierarchy and buses | Sub-networks as features; `#[interface]` ports with roles; `Bus<N>` | Role or port mismatch is a compile error | ELX-O-NET-1 | 3 |
| Net ties | `tie(net_a, net_b, at:)`; rule `named_net_join` | Unwaivable error naming the pin, nets and statements | ELX-O-NET-2 | 3 |
| Net partition for merges | Derived partition, nets matched by provenance | `Conflict::NetMerge` with pins, nets and Changes | ELX-O-NET-2 | 3 |
| Variant covering set | `#[configuration]` records under KLN's semantics (KLN-O-PLM-5); CI builds sellable configurations plus a pairwise covering set | An unbuildable configuration fails CI and is named | ELX-O-VAR-1 | 3 |
| Bare-board invariance | `bare_board_invariant` over every branch | Fails naming the configuration and the differing item | ELX-O-VAR-1 | 3 |

## Schematic capture and rule checks

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

**Decision D-ELX-27:** `Schematic` and `Layout` stay Ingot text with no binary sidecar: each is a module of `table { … }` literals whose rows are atomic merge blocks. *Why:* a second storage format would bypass block-level merge, live documents, span provenance, text-derived `CallSite`s and Git export (R9-34). *Rejected:* a binary sidecar keyed by statement identity, even as a fallback (R10-45); one module per board whatever its size.

ING's row lexer parses rows without the general tree and builds lossless nodes lazily on edit. The target is 10⁶ rows, about a 20-layer, 10,000-net board (estimate), parsed and hashed in under 1 s natively (ING-O-37). Above it, the layout splits into modules by board region, which merges and live documents already handle.

Editor behavior follows from D-ELX-1:

1. Drawing a segment writes a `connect` into the network block that owns both pins; crossing a hierarchy boundary adds a port. No-connect flags and net-tie symbols write `no_connect` and `tie`. Placing a label with an existing net's name writes a `connect`, and editing a label renames the net.
2. A connection made only in code renders dashed until one gesture draws it or places a label.
3. `schematic_matches_network` blocks release. A drawn group spanning two nets is `SchematicError::DrawnShort`, shown in the danger style; an item on a removed pin is `SchematicError::StaleAnnotation` with a one-click fix.
4. Moving a symbol edits one row of the `Schematic` module, so branches moving different symbols merge cleanly.
5. Connectivity generated by a loop is read-only in the drawing; editing it opens the generating line.

Off-page connections are labels with generated cross-references. Reference designators live in the module, change only by an explicit renumber shown as a diff, and never influence geometry (contract section 7.1). The editors run on UIX's canvases in the Electronics preset (D-UIX-27).

### Electrical rule checks

Electrical rule checks (ERC) live in `std::electronics::erc` and re-run only for the nets an edit touched; each has a severity, an explanation and a fix. `#[waive(…)]` in source only requests a Waiver; the rule fails until an authorized human signs a matching Waiver record (contract section 2). A Waiver whose rule no longer fires raises a warning.

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

Netlists export as SPICE, KiCad netlist and EDIF 2 0 0, the ANSI/EIA-548 version whose netlist view tools still support [95]. KiCad schematics import through an `io/` Wasm component: wires become `connect` statements, the drawing becomes the `Schematic` module, and near-miss wires are listed. Other tools arrive through ECO's migration path (R4-28), which ends in the same importer.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Drawn topology | Segments, junctions, labels, power symbols, sheet pins, no-connect flags, bus entries as table rows | `SchematicError::StaleAnnotation` with a fix | ELX-O-SCH-1 | 3 |
| Drawing matches network | `schematic_matches_network`, blocking | `SchematicError::DrawnShort` fails release | ELX-O-SCH-1 | 3 |
| Labels as connectivity | Label edit renames the net; an existing name writes a `connect` | Rename onto another net's name is a typed error naming both | ELX-O-SCH-1 | 3 |
| Reference designators | Stored and stable; explicit renumber as a diff | Duplicate designator is a `Failure` naming both Instances | ELX-O-SCH-1 | 3 |
| Pin and gate swap | Within catalog swap groups, from schematic or layout, as one source edit | Swap outside a group refused with the group | ELX-O-SCH-1 | 3 |
| ERC | Checks over the `Network` and catalog data, incremental by net; Waivers per contract section 2 | Violation with rule, location and fix; stale-Waiver warning | ELX-O-SCH-2 | 3 |
| Netlist export | SPICE, KiCad, EDIF 2 0 0 | Unsupported construct listed, never dropped | ELX-O-SCH-3 | 3 |
| Schematic import | KiCad directly; other tools through ECO's migration path | Near-miss wires and unmapped objects listed | ELX-O-SCH-3 | 3 |
| Design blocks | Sub-network plus layout fragment published as a package | A fragment that cannot place is reported; the schematic still applies | ELX-O-SCH-3 | 4 |
| Drawing output | PDF with title blocks and cross-references; lifecycle text late-bound | None expected | ELX-O-SCH-4 | 3 |
| Data modules at scale | `Schematic` and `Layout` as `table { … }` rows; region split above the parse target (D-ELX-27) | A module over the target is reported with its parse time and a split Proposal | ELX-O-SCH-5 | 3 |

## Catalog parts

### Electrical facets

A catalog part's definition is a signed data package under `parts::<manufacturer>::…`, pinned in `ingot.lock`, and its offers are External inputs (contract section 2). MEC owns its mechanical facets.

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

**Decision D-ELX-5:** Supplier offers enter evaluation only as signed, pinned External inputs changed by an explicit update, and BOM views date every offer. *Why:* stock changes hourly and principle 4 forbids reading live data, while cost checks still need prices. *Rejected:* live supplier lookups during evaluation; offers wholly outside evaluation, which hides cost from checks. (revised in round 2)

**Decision D-ELX-3:** A network element names an exact catalog part, an internal part number or a `CatalogSelection`, which re-resolves until the layout's first release. *Why:* designers state intent (`1uH ± 20%`) and a load change re-picks the inductor (R3-28), but a released part choice changes only by change order (R10-24). *Rejected:* resolving only at lockfile updates, which leaves picks stale; re-resolving after release, which swaps placed parts silently; calling a selection a `Query`; exact-only selection. (revised in round 3)

A selection is a pure function over pinned definitions, plus pinned offers when it ranks by price or stock. `crucible update parts` refreshes only the data pins and lists every substitution. A selection matching nothing fails with `SelectionError::NoCatalogMatch`, naming the tightest constraint and nearest candidates, and never widens its constraints.

When a board's layout is first released or locked, each selection records its part in the BOM data module as `resolved: parts::…`. Re-resolution then opens a Proposal with its reason ("selection now prefers X") instead of changing the part. A re-pick that changes the land pattern fails with `SelectionChangesLandPattern`, and ranked picks never change a released assembly BOM outside a change order.

**Decision D-ELX-22:** An organization parts-policy package lists approved internal part numbers (KLN `Purchased` Items) with approved manufacturers, lifecycle and preferred flags. A `CatalogSelection` resolves over approved parts first and reaches the open catalog only under a Waiver (contract section 2). *Why:* companies design with internal numbers their parts engineers control, so open-catalog picks alone make the design, ERP and assembly BOMs disagree (R4-20). *Rejected:* manufacturer part numbers only; an approved-parts database outside the repository.

BOM views list each internal number with its approved manufacturers. A new-part request is one Proposal creating the internal number, its facets and its approved manufacturers, and MEC's fastener selection reads the same policy.

### Footprints and symbols

Land patterns follow IPC-7351B by default, whose 2010 edition defines three density levels per package [55][56]. IPC lists IPC-7351B and the IPC-7352 guideline side by side among its current design standards [87]. Each generator reads its standard from a pinned package naming the document and edition, so moving to IPC-7352 is an explicit update (R4-42).

Footprint generators (`std::electronics::footprint::qfn`, `soic`, `bga`, `chip`, `sot`) compute toe, heel and side fillets from toleranced package dimensions. KiCad generates over 78% of its footprints from data [1]; Crucible's target is 100% for standard packages.

```
let fp = footprint::qfn(
    body: (4mm ± 0.1mm, 4mm ± 0.1mm), pitch: 0.5mm, pins: 24,
    lead_len: 0.4mm ± 0.05mm, exposed_pad: (2.6mm, 2.6mm),
    density: Density.nominal, standard: land_patterns::ipc_7351b,
)
.require(paste_coverage(fp.exposed_pad) in 50% .. 80%)
```

Symbols are generated from the pin table, the source, as KiCad 10's CSV pin tables suggest [1], and a librarian may refine the view. Alternate body styles follow the IEC 60617 database (IEC 60617:2026 [93]) or IEEE 315-1975, which IEEE has listed as inactive-reserved since 2019 [94].

### Creating and migrating catalog parts

1. **From a datasheet.** An agent extracts values into a record Proposal, citing page and table for each. AGT's quarantined `std::agents::extract` reads the datasheet, so the values are `data_untrusted` and the agent's context stays clean (D-AGT-25); a human approves.
2. **From libraries.** KiCad libraries import into organization-private packages, or into public packages licensed CC-BY-SA-4.0 with attribution kept, because KiCad's licence binds redistributed collections [104]. EAGLE XML arrives through ECO's importer, and Altium, CADSTAR, EasyEDA, P-CAD and Fabmaster files through KiCad 9's importers [66] in a pinned container.
3. **By hand.** The symbol and footprint editors write the same data modules.

Operator-curated `parts::` packages hold only cited facts and geometry from Crucible's own generators (D-ECO-18, R11-31). Manufacturer CAD files enter only where their terms allow redistribution.

Checks on every record: pins equal pads, the courtyard encloses the body, and pin types and SPICE port order match the IBIS pin list and pin map. Failures block publication with a `CatalogError` naming the facet.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Electrical facets | Versioned record of the facets above | A missing facet blocks only the uses that need it | ELX-O-CAT-1 | 3 |
| Consistency checks | Pins, pads, symbol, models and body agree | `CatalogError` blocks publication | ELX-O-CAT-1 | 3 |
| `CatalogSelection` | Pure over pinned definitions and offers; re-resolves when arguments change; recorded as `resolved:` once the layout is released | `SelectionError::NoCatalogMatch` with nearest candidates; `SelectionChangesLandPattern` | ELX-O-CAT-3 | 2 (selection over pinned definitions), 3 (offers, land patterns, layout release) |
| Offers | External inputs pinned in `ingot.lock`, dated in BOM views | An offer past its validity period is labelled with its age | ELX-O-CAT-3 | 3 |
| Parts policy | Approved internal numbers first; open catalog only under a Waiver | KLN's parts-policy check fails unless a Waiver names the part | ELX-O-CAT-4 | 3 |
| New-part requests | One Proposal creates the internal number, facets and approved manufacturers | Missing facets listed in review | ELX-O-CAT-4 | 3 |
| Footprint generators | Toleranced package dimensions to `Footprint` under a pinned land-pattern package | Dimensions outside a family are a typed error; `CatalogError::PinPadMismatch` | ELX-O-CAT-2 | 3 |
| Symbol generation | Pin table to symbol view | Unplaced pin listed; `CatalogError::SymbolPinMismatch` | ELX-O-CAT-1 | 3 |
| Datasheet extraction | PDF to a record Proposal with page references | Values without a source reference are rejected | ELX-O-CAT-5 | 4 |
| Library migration | KiCad, EAGLE and other libraries to catalog parts in private or CC-BY-SA-4.0 packages | Unmapped fields listed; the registry refuses a package without a redistributable data licence | ELX-O-SCH-3 | 3 |

## The board as a Part

### Stackup

A `Stackup` is an ordered list of layers plus the via spans a fabricator can build. Dielectric permittivity and loss are Fields over frequency, fitted with a causal multi-pole Debye model. Laminate records carry IPC-4101 slash-sheet designations (IPC-4101E-WAM1 [85]), and copper layers carry weight, `Tol<Length>` thickness, roughness and a role.

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

**Decision D-ELX-23:** A board declares `fab_class` and `assembly_class` (Class 1, 2, 3 or 3/A), selecting MFG rule packs pinned in licensed data packages. *Why:* the class changes annular ring, plating and acceptability rules, so checks must read it (R4-25), and Class 1 governs much consumer work (R10-34). *Rejected:* one rule set for every class; class as a drawing note only. (revised in round 3)

The current editions are IPC-6012F, IPC-A-610J and IPC J-STD-001J; IPC released the last two on 8 April 2024 [85][86]. MFG's fabrication-drawing generator writes ELX's class, materials, finish and impedance tolerances with the acceptance notes.

### Board geometry

**Decision D-ELX-6:** Authored layout geometry is integer data in nanometres per board, bounded to ±2^40 nm, with exact predicates through `anvil-planar` (D-ANV-27). *Why:* integer data makes DRC and fills identical everywhere at tens of bytes per track, and Crucible's fills pass its own exact DRC (R2-23). *Rejected:* copper as B-rep Bodies, too heavy for routing; floating-point coordinates; rounding to nearest; three-point arcs, whose offsets leave the grid (R8-22). (revised in round 3)

Tracks, pads, vias and zone outlines are integer points and segments. An arc is an integer centre, an integer radius and two integer direction vectors for its end rays, as ANV stores it (R8-22). Offsetting by an integer distance keeps the centre and rays and changes only the radius, so concentric clearances stay exact.

Only arc–arc and arc–line intersections snap, conservatively: fills inward and keep-outs outward. Three-point arcs from KiCad import convert under the same snap, and Bodies are derived on demand. Clipper2 offers integer polygon Booleans and offsets under BSL-1.0 but no arcs [47]; `anvil-planar` adds them.

| Derived Body | Representation | Consumers | Error bound |
| --- | --- | --- | --- |
| Laminate | BRep: outline extruded, holes removed | MEC fit, Flux structural, STEP | Exact |
| Copper layer *n* | Planar BRep from tracks, pads and fills | DRC, Flux, 3D view | Exact; chords within a stated tolerance (default 0.5 µm) |
| Copper solid | Copper layer extruded by its thickness | Local 3D EM and thermal zooms | As above |
| Assembled board | Laminate plus part bodies at placements | MEC, STEP AP242, IDX | The parts' import bounds |
| Envelope | Box, cylinder or prism per part | Fast clearance | Declared, conservative |

Silkscreen revision, date and serial text are late-bound placeholders, filled at output and excluded from KLN's definition digest (R4-17).

### One model with the enclosure

**Decision D-ELX-7:** The enclosure and the board live in one design repository and one Kiln graph, each able to drive the other's geometry. IDX serves only tools outside Crucible. *Why:* every exchange step can go stale, and even Fusion, with both domains in one environment, raises cross-domain changes as alerts to synchronize [57]. *Rejected:* an internal IDX-style baseline and increment protocol, which recreates the sync problem inside one product.

```
let board = pcb(stack, outline: enclosure.face(role: pcb_shelf).inset(0.5mm))
let mount = enclosure.bosses(m3) |> holes(board, plated: false, d: 3.2mm ± 0.05mm)
place(j1_usb, at: enclosure.cutout(usb).frame.on(board.top), lock: mech)
board.require(clearance(board.assembled(), enclosure.inner_body()) > 0.5mm)
     .require(aligned(j1_usb.body.face(role: mating), enclosure.cutout(usb), tol: 0.15mm))
```

When the USB cutout moves 2 mm, the connector follows on the next rebuild and DRC flags any track now too close. A `lock: mech` placement refuses drags; if referenced geometry disappears, the rebuild fails with a typed `ResolveError` and never keeps the old placement. Height limits arrive as keep-in volumes checked against the parts' 3D bodies.

### Boards from other tools

Enclosures are designed around boards from other ECAD tools long before ELX ships layout (R4-29). ECO imports IDF and STEP boards, which KiCad 9 exports [67], as read-only board Parts in phase 2. In phase 1, MEC checks enclosures against boards imported as STEP assemblies.

IDX V6 (December 2025) defers splines, 3D keep-outs and chamfered edges to V7 [14], and its change proposals arrive as Proposals.

### Rigid-flex and folding

A flex region carries bend lines with radius, angle and order. `anvil::fold` maps it onto cylinders with the neutral-layer offset from the flex stackup, and folded copper follows the same map. Checks follow IPC-2223, current at revision E [87]: minimum bend radius (larger for dynamic flexing), no vias in bend zones, staggered conductors and hatched planes.

Bend strain comes from a Flux laminate shell model as a `Field<Body, Strain>`, compared with the copper fatigue curve. The flat view feeds fabrication, and the enclosure assembly instantiates the folded view.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Stackup | Layers, Materials with laminate designations, `Tol` thicknesses, via spans, regions | `StackupError::UnsupportedSpan` naming the nearest span | ELX-O-BRD-1 | 3 |
| Fabrication and assembly classes | `fab_class` and `assembly_class`, Class 1 to 3/A, select pinned MFG rule packs | A class without a rule pack for the chosen fabricator is a typed error | ELX-O-BRD-1 | 3 |
| Layout geometry | Integer points, segments and centre-radius arcs; exact integer offsets of arcs | A construction that leaves the grid snaps conservatively, never to nearest | ELX-O-BRD-1 | 3 |
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

Interactive placement edits Instance `Transform`s in the `Layout` module: drag with live DRC, push, align, flip, arrays, rooms and channel replication by provenance. Network edits reach the board on the next rebuild with no annotation step. A removed Instance's orphaned tracks become DRC errors, never silent deletions.

Placement drag and the router run in the engine process on PLT's `Interactive` pool lane (R9-07). Pointer updates arrive as literal overrides through AGT's `edit.stream`, which ends in one `edit.apply` that writes the Change. Kiln never writes a result computed under overrides to the shared cache.

Cypress (ISPD 2025, Apache-2.0) places parts by gradient descent on wirelength, electrostatic density and a net-crossing penalty, but lacks height, thermal and critical-net terms [5][6].

**Decision D-ELX-8:** Automatic placement and routing are edit tools, never evaluation steps: each use writes ordinary `Layout` edits on a branch and opens a Proposal. *Why:* evaluations stay fast and deterministic, agents iterate on reviewable diffs, and a GPU optimizer's rounding never reaches a check. *Rejected:* placement or routing as Kiln-evaluated features, which would rewrite copper after every upstream edit.

The placer, a Wasm component, adopts Cypress's formulation and adds MEC's keep-in heights, thermal spreading, decoupling-loop length, critical-net proximity and designer locks. Its density solve calls `fft_solve` through `crucible:ops/flux`, and work is ordered by canonical numbers, never names. Targets: match Cypress's published results on its open suite, and place 500 parts in under 60 s on the reference laptop.

### Design rules and the constraint manager

Design rules are checks from `std::electronics::rules` in the design source, so they diff and merge. The constraint manager is UIX's grid over them, and editing a cell rewrites the expression.

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

**Decision D-ELX-9:** Rule precedence follows scope specificity, and an ambiguous overlap is an error that asks for an explicit `override`. *Why:* a designer sees which rule applies to any object, and an agent cannot change behavior by reordering rules. *Rejected:* numeric priorities, which hide intent (Altium's query rules [54]); a rule store beside the design, such as Altium's `Constraints.xml` [54].

Specificity runs from board default through layer, net class, class pair, net and net pair to object. The constraint manager shows winning and shadowed rules, and manufacturing limits come from MFG's rule packs.

**Decision D-ELX-28:** Spacing between nets that cross no safety barrier comes from `functional_spacing(nets)` over a licensed IPC-2221 package, at the nets' declared voltages. *Why:* 24 V, 48 V and 100 V buses need voltage-dependent spacing that fabricator minimums omit, so designers would otherwise hand-write rules (R10-25). *Rejected:* fabricator minimums only; isolation barriers for functional voltages, which misstate the insulation.

IPC-2221's current revision is C [87]. Its spacing categories cover internal conductors, uncoated external conductors below and above 3050 m, polymer-coated and conformally coated external conductors, and component leads [88]. The board's altitude and coating select the column.

A `conformal_coating` board record names the material, thickness and keep-out regions over connectors and test points. It selects the coated columns, feeds MFG's assembly package, and fails test-point access where coating covers a probe site.

**Decision D-ELX-24:** Safety spacing comes from a declared isolation barrier: end-product standard, insulation grade, working voltages, overvoltage category, pollution degree, material group and altitude. *Why:* end-product standards' tables differ from IEC 60664-1 alone, so spacing without grade, voltage form and altitude is wrong on safety-critical boards (R4-26). *Rejected:* a voltage and pollution-degree constructor; one default standard.

Barrier tables are licensed data packages per standard edition, such as IEC 62368-1:2023, IEC 61010-1:2010 with AMD1:2016, and IEC 60601-1:2005 with AMD1:2012 and AMD2:2020 [90][91][92]. Results carry the screening label, list the barriers checked, and apply slot and coating rules only where the standard permits.

**Decision D-ELX-30:** Standards and handbook tables are organization-licensed data packages, never std content, unless contract section 7.7 allows their licence. *Why:* IPC, IEC, Telcordia and FIDES sell or register each copy (FIDES needs registration [59]). *Rejected:* bundling every table in std; a redistribution exception per publisher.

### DRC

DRC is a set of checks over derived copper and holes, run by a Wasm component on `anvil-planar`, so every platform reaches one verdict. Kiln caches tiles, and an edit re-checks its tiles plus neighbours within the largest clearance. Distances are exact, and 3D checks refine envelope Bodies only where they collide.

Each violation names the rule, the shadowed rules and both objects, and suggests a fix such as "move 0.04 mm". Targets: full DRC of a 20-layer, 10,000-net board under 10 s on the reference laptop; incremental DRC after a routing edit under 50 ms.

### Interactive routing

KiCad's router shoves in an iterative loop over obstacles, with walk-back fallbacks, spring-back nodes and post-shove optimization [45]. Crucible keeps that structure and changes three things:

1. **Exact geometry.** Decisions use integer predicates, so a shove that passes in the router passes DRC.
2. **Rule-aware cost.** Costs read the rule set, including delay budgets. A shove that would push a matched net out of its window is refused, with the reason at the cursor.
3. **Recorded sessions.** Every gesture is recorded with its inputs, and UIX-O-ELX-1 replays ELX's sessions frame by frame.

Targets: under 16 ms per pointer update with up to 50 shoved items; finishing a route writes one Change within 50 ms.

### Length and delay tuning

Constraints may be stated in length or time, as KiCad 10 allows with per-layer profiles [1], but Crucible computes delay from physics. A cached Flux solve per cross-section gives delay over frequency, and stackup tolerances make each net's delay a `Tol<Time>`, matched worst case. Via and package delays come from per-via solves and IBIS package data, and tuning patterns keep self-coupling under a stated limit.

### Autorouting

**Decision D-ELX-10:** The autorouter is a search-based public Wasm component: flow escape routing, negotiated-congestion global routing, gridless A* detail, rip-up and reroute, and via-minimizing cleanup. *Why:* PCBWorld, an engine-grounded benchmark of 679 real boards, reports that learning-based routing still lags rule-based routers [30]. *Rejected:* an end-to-end learned router, unproven and hard to review; linking Freerouting, GPL-3.0 [35], which stays an external baseline over Specctra DSN and SES.

Learned models may supply cost hints through a Wasm component interface but never decide legality. Global routing follows PathFinder, McMurchie and Ebeling's negotiated-congestion router from FPGA 1995 [96]. Target: beat Freerouting's completion and via count on PCBWorld-Bench at equal or lower runtime.

Allegro X AI claims a 10× or greater turnaround reduction [40]. Quilter generates candidate boards by reinforcement learning under physics checks [41]; both claims are vendor-stated.

**Decision D-ELX-31:** Placer and autorouter work items open only after counsel's freedom-to-operate search of their code paths; learned hints train only on licensed corpora. *Why:* contract section 13.1 runs chain A's geometry in the same order, and PCBWorld states no licence for its corpus [30]. *Rejected:* building first and reviewing at release, which risks discarding finished work.

### Pours, planes and vias

**Decision D-ELX-11:** Zone fills are derived on every rebuild, never stored, and snap conservatively away from obstacles. *Why:* a stale fill is a known way to ship shorts or missing connections, and integer clipping by tile makes fills reproducible and fast. *Rejected:* stored fills refilled by hand before output. (revised in round 2)

- **Zones** have an outline, net, layers, priority, clearance, thermal reliefs, island policy and solid or hatched fill; equal-priority overlaps are an error.
- **Plane splits** are zones on plane layers; a check flags signals crossing a gap in their reference plane.
- **Vias** cover through, blind, buried, stacked and staggered microvias, via-in-pad, back-drilling with a stub rule, stitching and teardrops within the fabricator's HDI limits.
- **Via protection.** Each via class declares `protection: Ipc4761Type`, one of IPC-4761's seven types from tented to filled and capped [89]. The fabrication drawing states it, and a DFM rule checks it for via-in-pad (R10-34).

### Test points and the manufacturing handoff

`test_point(net, pad:, side:, min_pitch:, keepout_height:)` adds probe access, and an automatic Proposal adds test points to nets without access (R4-25, R4-24).

MFG owns the factory handoff (R3-25, R4-24, R4-27), and ECO owns every format writer and its phase. IPC-2581C [19][69], Gerber X2 and X3 at revision 2026.05 [15][16][17], drill files, IPC-D-356 test netlists [87] and ODB++ [18] arrive in phase 3. KiCad 9's ODB++ export [65] is an external oracle, and ELX shows writer findings, including IPC-2581C fabricator feedback, on the objects they name.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Interactive placement | Instance `Transform` edits with live DRC on the `Interactive` pool lane through `edit.stream` | Overlaps shown live; the edit is allowed and flagged | ELX-O-LAY-3 | 3 |
| Automatic placement | Placer to a Proposal (D-ELX-8) | Infeasible constraints named; a partial result is labelled partial | ELX-O-LAY-5 | 4 |
| Constraint manager | Grid over rule declarations with specificity precedence | Ambiguous overlap requires `override` | ELX-O-LAY-6 | 3 |
| Functional spacing | `functional_spacing(nets)` over a licensed IPC-2221 package; voltages from `Power` ranges and net classes | A net without a voltage range is a typed error naming it | ELX-O-LAY-6 | 3 |
| Conformal coating | `conformal_coating` record selects coated columns and keep-outs | A coated probe site fails test-point access | ELX-O-LAY-7 | 3 |
| Isolation barriers | Creepage and clearance per declared standard, grade and conditions | A barrier without a standard is an error | ELX-O-LAY-6 | 3 |
| DRC | Exact checks over derived geometry, incremental by tile | Violation with rule, shadowed rules, objects and fix | ELX-O-LAY-1 | 3 |
| Interactive routing | Walkaround, shove, highlight; 45°, 90°, free angle and arcs; differential pairs; drag | The head stops at the last legal point and shows the blocker | ELX-O-LAY-3 | 3 |
| Multi-track routing and fanout | Group routing at rule pitch; BGA and QFN escape | Members that cannot follow stop separately; unescapable pins listed | ELX-O-LAY-3 | 4 |
| Delay tuning | Field-solved delay as `Tol<Time>`; tuning patterns | An unachievable match reports the shortfall | ELX-O-SI-1 | 3 |
| Autorouting | Router to a Proposal | Unrouted connections listed; no Proposal carries DRC errors | ELX-O-LAY-4 | 4 |
| Zones, fills and teardrops | Derived on every rebuild, conservatively snapped | Equal-priority overlap is an error; islands handled per policy | ELX-O-LAY-2 | 3 |
| Vias and HDI | Spans from the stackup and the fabricator record; `protection: Ipc4761Type` per class | A disallowed span or stack is refused with the rule; via-in-pad without a filled and capped type fails DFM | ELX-O-LAY-1 | 3 (through, blind, buried), 4 (microvias, HDI) |
| Test points | `test_point` features; Proposals for nets without access | Untestable nets listed | ELX-O-LAY-7 | 3 |
| Board data for manufacturing | Board model read by ECO's writers, IPC-D-356 included, for MFG's packages; findings on board objects | A construct a writer cannot express is listed by that writer | ELX-O-DET-1 | 3 |

## Electrical analysis

Every analysis is an Ingot feature that builds a Flux problem or calls a solver Wasm component. It returns Fields with an `ErrorBudget` and a `ValidityEnvelope` at `Interactive` or `SignOff` fidelity, and Kiln re-runs only the analyses an edit touches. Screening results carry a screening label and never stand as compliance.

[[DIAGRAM diagrams/08-electronics-analysis-dataflow.jsx: electrical analysis dataflow · 7 analyses from one board model]]

Read it left to right: board data feeds seven analyses that return Fields and checks, and labelled arrows carry temperature and part power between them.

### Signal integrity

Impedance and RLGC come from a 2D quasi-static Flux solve per cross-section, with conductor loss, roughness and causal dielectrics. The solve holds below a tenth of a wavelength. Post-layout extraction splits nets into lines, vias and discontinuities, crosstalk covers aggressors within a reported window, and S-parameters use Touchstone 2.1 [20].

Macromodels use vector fitting (Gustavsen and Semlyen, 1999) with residue perturbation for passivity, as the SINTEF toolbox does [52]. Grivet-Talocia's Hamiltonian test checks passivity [97], and fit error enters the `ErrorBudget`. Fitting runs on `linalg`, since faer (MIT [48]) runs only in `CpuIsa` (contract section 7.1).

Channel simulation offers statistical eyes and bit-by-bit runs with IBIS 8.0 buffers, ratified on 5 December 2025 [21], and IBIS-AMI equalization. IBIS-ISS is at 1.0, and the parser is validated against IBISCHK8 [20].

**Decision D-ELX-12:** IBIS-AMI executables run only as External Ops on untrusted-evaluation workers, in a pinned host image per vendor platform (contract section 7.8). *Why:* AMI models are vendor-compiled native libraries that cannot be determinized, and an escape beside attestation keys would poison the shared cache (R5-03). *Rejected:* loading AMI libraries into the engine process; running them on trusted builders; accepting one untrusted run for a `SignOff` check (R11-08). (revised in round 3)

Gates and `SignOff` checks accept an AMI result only when two single-use runs on different hosts give one `ObjectId` in signed receipts (contract section 7.8). A nondeterministic model yields `Unverified` results, which meet a gate only under a policy allowance. Releases pin result `ObjectId`s, and a missing platform build is reported, never emulated.

### Power integrity

Target impedance per rail is allowed ripple over transient current. PDN impedance comes from Flux's layered sheets solving the Helmholtz equation per plane pair, coupled through via, capacitor and regulator models. Above the plane-pair limit, a full-wave solve is suggested.

Decoupling optimization picks capacitor types, counts and sites by greedy insertion and local search. IR drop solves DC conduction on per-layer copper sheets joined by via and plating resistances. A current-capacity screen follows IPC-2152, still current in its original revision [87].

Electro-thermal coupling is phase 4 (contract section 13.4): Flux uses monolithic Newton with continuation and reports `Runaway { power }` at the turning point (R1-49).

### EMC and EMI

ELX builds excitations and geometry; Flux solves the fields.

- **Radiated emissions.** Common- and differential-mode currents become current Fields on copper. Flux's FDTD (D-FLX-32) computes far fields at 3 m or 10 m with the enclosure, cables and harness in the model.
- **Conducted emissions.** A line impedance stabilization network sits in the simulation, with hot-loop parasitics from Flux extraction.
- **Immunity and ESD.** Port-level transient injections rank vulnerable nets.
- **Rule screening.** Every rebuild checks return-path breaks, slots under clocks, unstitched plane edges, long stubs and missing ground vias.

### Board thermal

Part power comes from simulation averaged over a stated window, a declared operating mode or datasheet values, labelled by source. Packages use two-resistor (JESD15-3) or DELPHI (JESD15-4) compact models [84], or the full package Body.

**Decision D-ELX-26:** At `Interactive` the board uses orthotropic conductivity per layer and tile from copper coverage. At `SignOff` it uses 2.5D layered conduction, per-layer thin sheets plus through-plane conductance, sharing the IR-drop machinery. *Why:* 35 µm copper on a 100 mm board is a 3,000:1 scale ratio over thousands of traces, which no volumetric octree resolves (R1-49). *Rejected:* explicit copper for the whole board; effective conductivity at `SignOff`, which hides hot spots under thin traces.

Explicit 3D copper serves only local zooms. Convection and the enclosure come from Flux conjugate heat transfer, laminar in phase 3 and turbulent in phase 4 (contract section 13.4).

Outputs are a `Field<Body, Temperature>` and junction temperatures as a `Field<Instances, Temperature>`. Checks compare them with limits and derating rules, and they feed back to simulation and IR drop.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Impedance and RLGC | Cross-section solve to `Field<Frequency, Rlgc>` with tolerance bands | Beyond the quasi-TEM limit flagged; a dielectric without frequency data names the Material | ELX-O-SI-1 | 3 |
| Post-layout extraction and crosstalk | Nets to S-parameters per net group; NEXT and FEXT within a reported window | An unmodelled discontinuity falls back to a full-wave solve, with its cost reported | ELX-O-SI-1 | 4 |
| S-parameter macromodels | Touchstone data through ECO's codec; vector fitting with passivity enforcement | Non-passive or non-causal data flagged per frequency; failed fit reports its worst error | ELX-O-SI-2 | 4 |
| Pre-layout topology and channels | Topologies and routed nets to eyes, timing and BER contours; AMI results accepted on matching receipts | A non-linear channel in statistical mode is refused; a missing AMI build is reported | ELX-O-SI-3 | 4 |
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

**Decision D-ELX-13:** Crucible's circuit simulator is a set of Rust Flux operations: modified nodal analysis, Newton with homotopy fallbacks, and BDF or trapezoidal integration. *Why:* it must run in Wasm with Flux's Fields and adjoints, faer breaks the canonical class (R1-10), and junction currents need `f64` (R1-39). *Rejected:* linking ngspice (LGPL and GPL-2+ files [8], no derivatives or Wasm parity); VACASK and Xyce (AGPL and GPL [9][60]); `f32` GPU batching. (revised in round 2)

The simulator factors with Flux's block-triangular LU in `linalg`, the KLU scheme reimplemented. Analyses are `F64Required`, and Monte Carlo runs one sample per CPU SIMD lane.

SPICE3 device models (diode, Gummel-Poon BJT, JFET, MOSFET levels 1 to 3, VDMOS) are ported from ngspice's BSD-3-Clause code with attribution [8]. Each is enabled after matching ngspice on a regression corpus.

**Decision D-ELX-14:** Crucible's Verilog-A front end, a public Wasm component, lowers compact models to the shared kernel IR (contract section 7.5). *Why:* BSIM, PSP, VBIC and many vendor models ship as Verilog-A, and one IR gives native speed, browser parity and a fixed operation order. *Rejected:* OSDI shared objects, native and platform-specific; Wasm-only device models, which lose derivatives and the fixed order. (revised in round 2)

Verilog-A constructs join the IR in phase 3. It emits canonical CPU and Wasm kernels with derivative Jacobians, keyed by source, front-end version and target.

**Decision D-ELX-25:** Vendor models run in ngspice as an External Op by default; encrypted ones run only in a vendor engine registered by the organization. *Why:* designers judge a simulator by whether vendor models run, and ngspice has added PSpice and LTspice compatibility over many releases [68] (R4-23). *Rejected:* listing vendor dialect constructs as unsupported until the native engine catches up; decrypting models; shipping vendor engines. (revised in round 3)

A vendor model moves to the native engine only after matching ngspice on its own test bench. For an encrypted model, the organization supplies the host image, accepts its batch-use terms and declares licence-server egress for an administrator to grant (contract section 7.8). That host receives only inputs labelled at most `internal` without `controls`, unless a two-person grant names it.

Gates accept vendor-model results on matching receipts, as for AMI results (D-ELX-12). The netlist importer reads ngspice, PSpice and LTspice dialects, lists unsupported constructs with file and line, and stores imported text for review.

### Analyses and results

Simulation results carry an `ErrorBudget`. Algebraic error is `Estimated` from residuals, input error comes from `Tol` propagation, and model form is `NotQuantified` unless a device envelope cites a validated bound. A check on them is therefore a conditional `Pass`, which meets a release gate only under a policy allowance (contract section 5).

Temporal error follows FLX's rule: summed local truncation errors are `Indicator`, because phase error accumulates in oscillators, LC tanks, PLLs and switching converters (R7-22). The temporal part is `Estimated` only when `solve_dae` runs the adjoint-weighted estimate for the checked goal (FLX-O-ERR-6), or step-halving with frozen breakpoints calibrates it. Each transient check states which applies, so no `SignOff` check passes on an indicator.

Monte Carlo draws from `Tol` distributions with ING's correlation groups, so parts from one reel move together. Random streams come from KLN's `OpCx::rng`, keyed by sample index, never by class, fidelity or names (contract section 7.2). Added samples never change earlier ones.

Targets: C6288 with PSP103.4 models within 1.2× of VACASK's time; 10,000 samples of a 200-node circuit's AC response in under 60 s on the reference laptop.

### Mixed-signal

An event-driven digital kernel in the style of XSPICE provides four-state logic with threshold and hysteresis bridges, and digital events become analog breakpoints. Verilog blocks compile with Verilator (LGPL-3.0 or Artistic-2.0 [29]) and run as External Ops; microcontrollers run real firmware in Renode (D-ELX-18).

### Reliability prediction and derating

Reliability prediction gives failure rates for comparison and allocation. Every result names its handbook, because handbooks disagree by large factors.

| Method | Edition | Use |
| --- | --- | --- |
| FIDES | Guide 2022 Edition A; registration required [59] | Default for new designs |
| Telcordia SR-332 | Issue 4, March 2016 [58] | Telecom |
| MIL-HDBK-217F | Notice 2 [58] | Legacy and defence |
| IEC 61709 via SN 29500 | Reference conditions converted to operating ones [58] | Industrial |
| Physics of failure | Engelmaier and Coffin-Manson solder fatigue on Flux strain; Black's equation; Arrhenius wear-out | Critical joints and parts |

Crucible ships the engines, and handbook tables are licensed data packages (D-ELX-30). Mission profiles are Ingot values, so part stresses per phase come from simulation and thermal results. Derating follows ECSS-Q-ST-30-11C Rev.2 of 23 June 2021 [74], and fault trees from the `Network` hierarchy feed FMEA tables in `std::systems`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Operating point | Newton with damping; gmin, source stepping and pseudo-transient homotopy in order | Non-convergence returns the largest-residual nodes and a fix, such as a missing DC path | ELX-O-SIM-1 | 3 |
| DC sweep | Continuation over a source value to `Field<(Ports, Voltage), Current>` | As operating point, per point | ELX-O-SIM-1 | 3 |
| AC and noise | Linearized complex LU per frequency to `Field<(Ports, Frequency), Complex<Voltage>>`; adjoint noise | A singular matrix names the floating node set | ELX-O-SIM-1 | 3 |
| Transient | BDF and trapezoidal with LTE control, breakpoints and ringing detection, to `Field<(Ports, Time), Voltage>`; temporal error `Indicator` unless adjoint-weighted or step-halving verified | `StepTooSmall` with time, device and nodes | ELX-O-SIM-1 | 3 |
| Pole-zero and loop stability | Generalized eigenvalues; Middlebrook [98] or Tian [99] loop gain; margins | As AC | ELX-O-SIM-1 | 3 |
| Monte Carlo and corners | `Tol` samples with correlation groups, one per SIMD lane | Failed samples counted and reported, never dropped | ELX-O-SIM-4 | 3 |
| Sensitivity and worst case | Adjoint DC, AC and transient sensitivities; corner search confirmed by simulation | None beyond the analysis | ELX-O-SIM-4 | 4 |
| Periodic steady state and harmonic balance | Shooting Newton; harmonic balance for mixers and amplifiers | Divergence with iteration history | ELX-O-SIM-1 | 5 |
| Vendor models | ngspice External Op; native after a matched test bench; encrypted models in organization-registered engines | Host failure is a `Failure` with the host log; worker loss is an Abort; differing receipts give `Unverified` | ELX-O-SIM-2 | 3 |
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

**Decision D-ELX-16:** Efficiency and loss maps come from Flux magnetostatic solves per (id, iq) point, with motion through Flux's sliding interface or mortar coupling. Points solve in parallel and cache individually. *Why:* map points are independent, so Kiln reuses every point after an edit that changes only the control strategy. *Rejected:* analytic machine models only, which miss saturation and slot effects; one transient solve per operating point, far costlier than a map needs.

Solenoids and voice coils use magnetostatic force maps; piezo stacks use Flux's piezoelectric model with a Butterworth-Van Dyke lumped equivalent from phase 5.

### Sensors and drives

A sensor has three layers: optional Flux transduction physics, a behavioral element (transfer, noise, drift, quantization) and a register interface. Register maps come from CMSIS-SVD or SystemRDL, and Renode generates peripheral stubs from SystemRDL and register tags from SVD [79]. The sensor's error budget is a check over the three layers, such as encoder angle error under 0.1°.

Inverters range from averaged models to switching models with losses from catalog switching-energy curves. ELX's drivetrain elements let GP3's gearbox and ideal sources form one drivetrain from phase 2, with a lumped motor from phase 3.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Machine geometry features | Typed parameters to machine Bodies and winding layout | Slot overlap or negative tooth width is a typed error | ELX-O-MCH-1 | 4 |
| Lumped machine model | dq element with saturation tables | Operation outside the tables is flagged, never extrapolated | ELX-O-MCH-1 | 4 |
| Flux-linkage, torque and loss maps | Batched magnetostatic solves with interpolation error | Unconverged points marked in the map | ELX-O-MCH-1 | 4 |
| Transient machine `SignOff` | Magnetodynamics with motion coupled to the drive Network | Divergence reported with time and region | ELX-O-MCH-1 | 4 |
| Actuators | Force maps and lumped equivalents (4); piezo stacks (5) | As machine maps | ELX-O-MCH-2 | 4, 5 |
| Sensor models | Three layers with an error budget as a check | A missing layer leaves the budget `Undecided` | ELX-O-MCH-2 | 4 |
| Drive models | Averaged and switching inverters with losses | Missing switching curves listed | ELX-O-MCH-2 | 4 |
| Drivetrain coupling | ELX's drivetrain elements with ideal sources (2) or a lumped DC motor (3) in one Network | Port domain mismatch is a compile error | ELX-O-NET-3 | 2, 3 |

## Controls and co-simulation

### Representations

Control design uses plain Ingot values, with no separate block-diagram language.

| Representation | Type | Operations |
| --- | --- | --- |
| Transfer function | `Tf<In, Out>` over s or z, `Quantity` coefficients | Feedback, discretization (ZOH, FOH, Tustin), minimal realization |
| State space | `Ss<In, Out>` with typed signals | Controllability, observability, balanced truncation |
| Frequency response | `Zpk`; `Field<(Ports, Frequency), Complex<Ratio>>` for measured data | Bode, Nyquist, Nichols, margins |
| Block diagram and hybrid | A `Network` of signal ports; state machines with typed events | Flattening to state space; event detection |

A gain from a position error in metres to a torque has type `Quantity<Torque / Length>`, so a missing conversion fails at compile time. Plants come from Networks, reduced Flux models and Flux multibody models of MEC assemblies, linearized by `flux::linearize_multibody` (R9-30). A Flux structural mode becomes a plant pole pair, so GP6's attitude loop is checked against frame resonances.

Controllers export as C with a harness that matches the Ingot reference bit for bit, and the code is a Software item.

### Co-simulation

**Decision D-ELX-17:** An FMU instance is a `Network` element with ports and units from its model description, run by Flux's FMI and SSP runtime (D-FLX-30). *Why:* one runtime ends round 1's duplicate FMI specifications (R3-24), while FMUs still join drives and plants through ordinary `connect`. *Rejected:* a second FMI master in ELX; FMUs outside the Network model. (revised in round 2)

ELX owns bus simulation over FMI-LS-BUS. Flux's runtime implements FMI 3.0.2 [12] and SSP 2.0.1 [11][13], and FMU export and SSP are phase 4 (contract section 13.4).

FMI-LS-BUS 1.0 (21 July 2025) covers the CAN family, a 1.1 beta adds FlexRay and Ethernet [26], and a 1.3 beta adds LIN [27]. Its demo FMUs cover CAN and FlexRay [80].

Modelica arrives through FMUs; its Standard Library is BSD-3-Clause, at v4.1.0 [61]. OpenModelica is AGPL-3.0 for non-members under OSMC-PL 1.8 [63], so it runs only as an external tool. Rumoca, an Apache-2.0 Rust compiler its authors call rough-edged [50], is a phase 5 option for Flux's Network compiler, which follows ModelingToolkit [51].

### Firmware-in-the-loop

**Decision D-ELX-18:** Renode is the default firmware emulator and QEMU the alternative for application processors, both as External Ops on Linux x86-64 untrusted-evaluation workers. *Why:* Renode is MIT and runs unmodified Arm, RISC-V, x86 and Xtensa binaries [28], and firmware is untrusted code kept from attestation keys (R5-03). *Rejected:* a Crucible emulator, duplicating a mature effort; single-family vendor simulators; emulators in the engine process. (revised in round 3)

Renode models multi-node networks [28] and co-simulates RTL through Verilator [62]. It publishes Linux, Apple-silicon macOS and Windows packages but no ARM64 Linux package [28], so ARM64 server classes send firmware runs to x86-64 workers.

1. **Peripheral bridge.** Pins, ADCs, timers, PWM and serial buses map to nets or signal ports from the pin facet and board description, checked every rebuild.
2. **Lock-step time.** Emulator and network advance in quanta (default 10 µs). PWM edges and ADC samples cross as timestamped events, and results report the quantum's timing error.
3. **Determinism.** With fixed quantum, seeds and peripheral models, runs repeat, and the ELF hash enters the key. Renode calls its environment deterministic [62]; ELX-O-FW-1 checks it per Renode release, and a run that differs on repeat is `Unverified` (contract section 7.8).
4. **Tests.** DWARF variables appear beside circuit signals, and firmware tests are checks, such as `require(settle_time(motor.speed, to: 3000rpm, within: 2%) < 150ms)`.

### Hardware-in-the-loop and flashing

Real-time execution lies outside Kiln: plants export as FMUs or fixed-step C, and benches run as KLN's enrolled physical-test runners (D-KLN-35) talking to `api`. A run is an Evidence record signed with a TPM-held device key (contract section 7.1), never a cached result. An Evaluation reads the newest record valid at its measurement time, up to its evidence watermark (contract section 2).

**Decision D-ELX-29:** Every client flashes a board only through the transfer Act `flash_device` (contract section 7.6). *Why:* firmware runs when the core leaves reset, so flashing a motor controller, ESC, heater driver or charger starts motion or energy (R10-06). *Rejected:* flashing outside Crucible's record; flashing as an ordinary write, which would start devices without an Approval.

1. **Plan.** It names the Software item version, image digest, target board serial, and probe or bootloader.
2. **Write.** The bench adapter or gateway writes the image and reads back its digest. The target stays halted or held in reset until a person at the bench releases it.
3. **Approval.** It covers the image digest and target. The approval page lists Network hazards (rotational ports, heaters, high voltage) with a "remove propellers and loads" step.
4. **Clients.** `apps/platform` and WebUSB flash through the same Act; on an `unattended_safe` rig, `run_rig_test` covers flashing.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Transfer-function and state-space algebra | Typed signals, discretization, realization | Unit mismatch around a loop is a compile error | ELX-O-CTL-1 | 4 |
| Linearization | Exact Jacobians of Network plants through Flux derivatives and of multibody plants through `flux::linearize_multibody` | A non-smooth operating point (contact, saturation) is flagged | ELX-O-CTL-1 | 4 |
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
| Hardware-in-the-loop | Plant FMUs or fixed-step C out; Evidence records in, read up to the evidence watermark | Variable-step constructs refused; evidence on an incompatible version does not count | ELX-O-FW-2 | 4 |
| Firmware flashing | `flash_device` plan with image digest, board serial and probe; read-back; target left in reset; hazards from the Network | A read-back mismatch fails the Act and keeps the target in reset | ELX-O-FW-3 | 3 |

## Batteries and power electronics

### Cell models

Cell models form a ladder, each rung with its envelope. Parameter sets are Materials (COV) whose fitting conditions become part of the envelope.

| Model | Equations | Valid for | Phase |
| --- | --- | --- | --- |
| Equivalent circuit | OCV(SOC, T), R0 and RC pairs; LFP hysteresis by PyBaMM's one-state model [70], fitted to LFP charge and discharge data | Pack and BMS design in the fitted range | 4 (contract section 13.4) |
| SPMe | One particle per electrode plus electrolyte transport | Moderate rates | 4 (contract section 13.4) |
| DFN (P2D) | Porous-electrode theory over a particle-radius domain (D-FLX-38) | High rates, plating risk | 5, FLX (contract section 13.4) |
| Swelling and stack pressure | Ai et al.'s swelling model as PyBaMM implements it [71]; cell thickness against state of charge with pad stiffness | Within the tested pressure range | 4 (contract section 13.4) |
| Degradation | SEI growth, plating, loss of active material | Within the tested conditions | 5 |
| Abuse mechanics | Wierzbicki and Sahraei's homogenized jellyroll [72] with failure strain, coupled to runaway screening | Crush, penetration and crash screening | 6 (contract section 13.4) |

ELX-O-BAT-1 counts the hysteresis model only after its parameters are fitted to LFP data (R7-41). The abuse model enters phase 6 only once its calibration reproduces on the GP12 cell's crush tests.

**Decision D-ELX-19:** Equivalent-circuit cells are Network elements and SPMe cells are Flux forms, with PyBaMM as the reference for oracles and parameter sets. *Why:* PyBaMM is BSD-3-Clause with SPM, SPMe and DFN [42][43], while native models give derivatives, Wasm portability and Flux thermal coupling. *Rejected:* embedding PyBaMM, which puts a Python runtime in evaluation; DFN as an ordinary form, which needs nested domains (R1-24). (revised in round 2)

DFN cells use Flux's parameter-domain forms (D-FLX-38), and pack-scale models embedding them follow in phase 6.

### Pack design

A pack is an Assembly of cell Instances, busbars, a BMS board and an enclosure, and ELX adds its electrical meaning:

- **Topology.** A `14s4p` arrangement generates the Network, each cell perturbed by its own parameters.
- **Busbars.** Flux DC conduction gives resistance and Joule heat; joint resistance is an element with stated uncertainty.
- **BMS.** A board designed here, running as models or real firmware.
- **Thermal and swelling.** Cell heat goes to Flux conjugate heat transfer; swelling sets pad compression and stack-force checks (R1-40).
- **Safety.** Fuse coordination, isolation barriers (D-ELX-24) and runaway propagation screening from published calorimetry.

### Power converters and magnetics

`std::electronics::power` provides buck, boost, flyback, forward, LLC, full-bridge, dual-active-bridge, PFC and inverter features returning Networks. Averaged models give part stresses that become `CatalogSelection` constraints. Losses become power Fields, and hot-loop inductance from Flux extraction bounds switch-node overshoot.

| Quantity | `Interactive` method | `SignOff` method |
| --- | --- | --- |
| Core loss | iGSE with DC-bias correction; MagNet-trained models where available | Same, with flux waveforms from a Flux solve |
| Winding loss | Dowell (1966) [100]; Albach and Lammeraner for round wire, Albach and Ferreira for Litz [53] | 2D or 3D Flux eddy-current solve of the window |
| Inductance and leakage | Reluctance network with Roshen fringing and Zhang gap reluctance [53] | Flux magnetostatic solve |
| Capacitance and thermal | Albach winding capacitance [53]; thermal network | Flux electrostatic solve; conjugate heat transfer |

The MagNet Challenge 2023 benchmarked data-driven magnetics models and reported large gains in accuracy and size in 2025 [39]; Crucible adopts its dataset and metric. OpenMagnetics MKF is MIT [53] and a candidate for porting. A designed transformer gets an item number and a BOM like any Part.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Equivalent-circuit cells | OCV, resistance, RC pairs and an optional fitted one-state hysteresis as a Network element | Operation outside the parameter set's range is flagged with the variable | ELX-O-BAT-1 | 4 |
| SPMe cells | Forms with a parameter-set Material, to voltage, temperature and concentration Fields | As above | ELX-O-BAT-1 | 4 |
| Parameter fitting | Measured data to a set with confidence intervals | Unidentifiable parameters reported, never fixed silently | ELX-O-BAT-1 | 4 |
| Swelling and stack pressure | Ai et al.'s expansion and pad stiffness to pressure and force Fields | Outside the tested pressure range flagged | ELX-O-BAT-2 | 4 |
| Pack Network, busbars and thermal | Series-parallel layout with per-cell variation; Flux conduction and heat transfer | Inconsistent count or orientation is a compile error; limits fail checks | ELX-O-BAT-2 | 4 |
| Pack safety screening | Fuse coordination, barriers, runaway propagation | Results labelled as screening | ELX-O-BAT-3 | 6 |
| Abuse mechanics and pack-scale DFN | Homogenized jellyroll failure model coupled to runaway screening; DFN cells in pack thermal | Outside the envelope the zone is `Invalid` and checks refuse | ELX-O-BAT-3 | 6 |
| Converter topologies and loops | Parameters to Networks with selection constraints; compensators with margins | An infeasible duty cycle is a typed error; an unstable loop fails with its margins | ELX-O-PWR-1 | 4 |
| Losses and parasitics | Loss Fields; hot-loop inductance from Flux extraction | Missing loss curves leave the check `Undecided` | ELX-O-PWR-1 | 4 |
| Magnetics design | Core, winding and gap to losses, inductances and Bodies | Saturation at peak current fails the check | ELX-O-PWR-2 | 4 |

## Wire harnesses

MEC owns 3D routing and formboard geometry, ELX owns connectivity, wire tables and electrical checks, and MFG owns the harness manufacturing package (R4-30). ELX's part lands in phase 4, when GP6 needs it; MEC's phase 3 routing uses declared bundle diameters until then.

- **Connectivity.** A harness is a `Network` of connector, wire, splice and terminal catalog parts, joined to board ports by `connect` into one netlist.
- **Wire table.** Per variant: ends, gauge, colour, cut and strip lengths, terminal and seal part numbers, and the terminal maker's crimp height and pull force.
- **Lengths.** MEC's routed paths plus service loops and termination allowances.
- **Checks.** Gauge against current with bundle derating, voltage drop, pin ratings, terminal and seal compatibility, shield termination.
- **Package data.** Connector face views from the mating side, splice and marker lists, a continuity and insulation test netlist, and the IPC/WHMA-A-620F workmanship class [85]. MFG combines them with MEC's 1:1 formboard.
- **Exchange.** VEC 2.2.0 is VDA 4968 and prostep ivip PSI21, and VEC 1.1.2 absorbed KBL 2.4 features [22]. ECO's codec reads and writes VEC in phase 4, and reads KBL 2.5 SR-1, the current version [73], in phase 5.

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
| SDFormat | Worlds, models, sensors, closed loops | 1.12, the newest specification version [75] |
| MJCF | Bodies, joints, actuators, tendons, sensors, contact | MuJoCo is Apache-2.0 [24]; sdformat_mjcf converts from SDFormat [25] |
| USD | Visual and physics schemas | Through an `io/` writer; gz-usd converts SDF [25] |

Collision geometry comes from `anvil::convex_decompose` with a stated Hausdorff bound, and exports carry their Change id. Crucible generates colcon-buildable packages for the newest LTS distribution that REP 2000 lists, now Jazzy Jalisco, supported until May 2029 [76]. Even-year releases are LTS, so Lyrical Luth, the May 2026 release [23], becomes the target once REP 2000 lists its platforms.

MuJoCo and Gazebo run as External Ops, and CI loads every export in both. A planning hook sends the model and collision Bodies to an external planner such as MoveIt. Trajectories return as `Field<(Instances, Time), Transform>`, along which torque, current and temperature are checked.

Sending a robot program is the `send_robot_program` Act, and Crucible never starts motion (contract section 7.6).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Kinematic chain view | Assembly with MEC joints to links, joints and attached models | A joint lacking limits or an actuator where an export needs one is reported | ELX-O-ROB-1 | 4 |
| URDF, SDFormat and MJCF export | Chain to files with stated mesh error | A cut closed loop is reported | ELX-O-ROB-1 | 4 |
| USD export | Chain to USD physics schemas | Unmapped elements listed | ELX-O-ROB-1 | 5 |
| ROS 2 description package | Chain to a colcon-buildable package for the current LTS distribution | A failed build is reported with its log | ELX-O-ROB-1 | 4 |
| Planning hooks | Model and collision world out, trajectory Field back | Planner failure returned as a typed error with its message | ELX-O-ROB-2 | 5 |
| Trajectory checks | Trajectory to torque, current and temperature checks | Exceedance fails with time and joint | ELX-O-ROB-2 | 4 |

## RF: antennas and matching networks

Antennas are Bodies: board copper, stamped metal, flex or coatings on the enclosure. `std::electronics::rf` provides patch, inverted-F, PIFA, monopole, dipole, loop, helix, slot and array features returning Bodies and ports. Board antennas are layout items under DRC.

Flux owns the solvers (D-FLX-32): frequency-domain Nédélec FEM for resonant antennas and FDTD for broadband problems (R1-22). Antennas are analysed in their housing, a Material without frequency-dependent data is an error, and specific absorption rate is screening only.

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

**Decision D-ELX-20:** The system model is native Ingot in `std::systems`, and SysML v2 is an exchange format through its textual notation and the Systems Modeling API. *Why:* one language keeps one model with three editors, and requirements reference real Parts, nets and checks with checked units. *Rejected:* SysML v2 as a second authoring language, a second source of truth; SysML v1 XMI exchange, which loses semantics. (revised in round 2)

`std::systems` records mirror SysML v2 part and port definitions, connections, requirements, actions, states, constraints, allocations and variation, with a semantic mapping per concept. Crucible's own parser and serializer, an `io/` Wasm component, follow the published grammar with the pilot implementation as reference [31]. Unmapped concepts survive as opaque annotations.

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

- **Typed links.** `satisfy`, `verify`, `derive` and `allocate` point at Instances, checks, nets or requirements through `Query`s resolved every rebuild. A broken link is a `ResolveError`.
- **Computed status.** Status follows from `CheckOutcome`s: verified, failing, undecided, conditional, unverified, outside an envelope, or covered by a Waiver. Evidence records count only on the same design or a declared compatible one.
- **Computed impact.** A requirement edit re-evaluates only dependent checks, and a Proposal shows status changes beside geometry and metric diffs.
- **Exchange.** ReqIF passes through an `io/` Wasm component, keeping external ids; imported text arrives as `ExternalText`.

### Software and firmware as BOM items

A Software item (contract section 2) records its item number, version, binary hashes, source repository and Change, and toolchain. Its software bill of materials is SPDX 3.0 or CycloneDX 1.7 [82][83].

Its `ItemDefinition` holds the binary hashes, the software bill of materials digest, the `load` bindings and the toolchain digest (contract section 5). A release's approval subject covers that definition, so swapping a binary after approval voids the Approval (R9-01, R11-17).

1. **Binding.** A `load` relation binds a Software item to a programmable Instance per configuration, and the BOM lists it under the programmed assembly.
2. **Hardware contract.** Crucible generates a board description (pins, peripherals, clocks, memory map) as a Zephyr devicetree overlay or a Rust board-support crate. Firmware declares the description hash it was built against, and a check compares it: "Firmware 1.4.2 expects the status LED on PA5; board revision C routes it to PB3."
3. **Reproducibility.** CI rebuilds firmware in a pinned container as an External Op; a hash mismatch fails the release check.
4. **Release.** A signed release records board revisions, Software item versions and their compatibility matrix.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `std::systems` modeling | Requirements, architecture, functions and allocations as Ingot records | Broken links are `ResolveError`s | ELX-O-SYS-1 | 3 |
| Computed requirement status | Status from check outcomes, Waivers and Evidence records | Evidence on an incompatible version excluded, with the reason | ELX-O-SYS-1 | 3 |
| SysML v2 exchange | Textual notation and API to and from `std::systems` | Unmapped concepts kept as annotations | ELX-O-SYS-2 | 4 |
| ReqIF exchange | Requirements with external ids | Unmapped attributes kept as annotations | ELX-O-SYS-2 | 4 |
| Software items | Hashes, software bill of materials and `load` bindings in the `ItemDefinition` | A board-description mismatch fails the release check; a binary swap voids the Approval | ELX-O-SYS-3 | 3 |
| Firmware reproducibility | Pinned-container rebuild and hash comparison | A mismatch fails the release | ELX-O-SYS-3 | 4 |

## State of the art

Commercial tools are named as reference products only, with no claim about their internals. Every figure is a target.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Connectivity capture | Drawn schematics with ERC (KiCad 10 [1]); code capture with part picking (atopile [4]) | Altium, KiCad 10, atopile | Code as source with a checked drawing (D-ELX-1) | Net-merge conflicts 100% flagged; ERC recall 100% |
| Land patterns | Tolerance-driven IPC-7351B patterns [55] | KiCad, over 78% generated [1] | 100% generated for standard packages | 2,000 packages within ±1 µm of an independent calculation |
| Automatic placement | Analytical placement with net-crossing relaxation (Cypress [5]) | Cypress [6]; Allegro X AI [40]; Quilter [41] | Cypress plus height, thermal, decoupling and critical-net terms | Cypress's published results on its open suite |
| Interactive routing | Push and shove with walkaround and spring-back (KiCad [45]) | KiCad 10, Allegro, Xpedition | Same structure on exact geometry, delay-aware | Replayed sessions against the routing targets |
| Autorouting | Negotiated congestion [96] with gridless detail; learned routers trail (PCBWorld [30]) | Freerouting [35] | Search-based Wasm router (D-ELX-10) | PCBWorld-Bench: higher completion and fewer vias than Freerouting |
| DRC | Incremental, indexed, exact predicates | Altium, Allegro, KiCad | Tiled integer DRC on `anvil-planar` | 10 s full, 50 ms incremental; zero disagreements with a rational reference |
| Delay tuning | Time-domain constraints with per-layer profiles (KiCad 10 [1]) | KiCad 10, Allegro | Field-solved delay with tolerance propagation | TDR delay on GP5 coupons, ±2% |
| Cross-section RLGC | 2D quasi-static solution with roughness and causal dielectrics | Polar Si9000, HyperLynx | Flux 2D solve cached per cross-section | Conformal mapping and coupons, ±3% on Z0 |
| S-parameter macromodels | Vector fitting with passivity enforcement [52][97] | SINTEF toolbox [52] | Rust fitting, Hamiltonian check, residue perturbation | 100% passive; fit error at most the toolbox's |
| Channel simulation | Statistical eye and bit-by-bit with IBIS-AMI [20][21] | Sigrity, HyperLynx | Both modes; AMI as External Ops | IEEE 802.3ck contributed channels with its COM tool [101]; eye height within 5% of a commercial tool |
| PDN impedance | Plane-pair cavity models with via coupling; full wave above their limit | Sigrity PowerSI, HyperLynx PI | Layered sheets in Flux | Analytic resonances ±2%; VNA on GP5 ±15% |
| IR drop and board thermal | DC conduction with thermal coupling; layered board conduction | Sigrity PowerDC | Thin sheets, monolithic electro-thermal Newton; D-ELX-26 | Analytic ±1%; four-wire ±5%; GP5 thermocouples ±5 K |
| Antennas | Nédélec FEM with wave ports and fast sweep [33] | Palace [33]; openEMS [32] | Flux frequency-domain solver (D-FLX-32) | Hallén dipole and cavity patch; resonance within ±1% of Palace |
| Analog simulation | Modified nodal analysis, homotopy, block-triangular LU | VACASK [9]; ngspice for compatibility [7] | Rust engine plus ngspice for vendor models (D-ELX-13, D-ELX-25) | Vendor corpus 95%; C6288 within 1.2× of VACASK |
| Compact models | Verilog-A compiled to OSDI (OpenVAF [10]) | OpenVAF with ngspice or VACASK | Own front end to the kernel IR (D-ELX-14) | BSIM4, PSP and VBIC curves, relative 10⁻⁶ |
| Reliability prediction | FIDES 2022 physics-informed models [59] | Tools covering SR-332 and FIDES [58] | Four handbooks plus physics of failure | Worked examples to printed precision |
| Electric machines | Transient FEM with motion and loss models | Ansys, JMAG; Pyleecan with FEMM [44] | Flux maps plus transient `SignOff` (D-ELX-16) | TEAM problem 30a, induction motors [81]; GP6 dynamometer, ±5 points |
| Magnetics core loss | MagNet data-driven models [39]; iGSE | OpenMagnetics MKF [53] | iGSE plus MagNet-trained models | MagNet metric no worse than the published winners |
| Battery cells | SPMe and DFN with SUNDIALS solvers | PyBaMM [42][43] | Native ECM and SPMe; DFN through Flux (D-ELX-19) | 1 mV RMS against PyBaMM on 1C discharge |
| Control design | Riccati, structured H∞, conic MPC | MATLAB Control System Toolbox | Rust on `linalg`; MPC through Clarabel [49] | Closed-form cases, relative 10⁻⁹; the 138-problem Maros-Meszaros QP set [102] |
| Firmware-in-the-loop | Instruction-level emulation with peripheral models | Renode [28]; QEMU | Renode in lock-step (D-ELX-18) | Identical traces in 100% of repeated runs |
| Harness data | VEC 2.2.0 [22] | Zuken E3.series, Capital | Harness Network with VEC exchange | Zero dropped elements in round trips |
| Robot descriptions | URDF, SDFormat and MJCF with converters [24][25] | Hand-written descriptions; CAD exporters | Generated from the Assembly | Mass properties to relative 10⁻⁹; clean loads in MuJoCo and Gazebo |
| System modeling | SysML v2 with KerML and the API [2][3][31] | Pilot implementation [31] | Native `std::systems` (D-ELX-20) | Pilot examples round trip; OMG suite when published |
| Matching networks | Real-frequency matching; Bode-Fano bound | Optenni Lab with vendor component libraries [103] | Synthesis with real parts and yield | Analytic L-networks to 10⁻⁶; bound never exceeded |

## Platform notes

- **Integer board data.** Layout, DRC, fills and the board model hash identically on every Tier 1 platform, browsers included. Chord points come from `detmath`, and silkscreen text uses `anvil::text_outline` over registry font packages (D-PLT-7).
- **External Ops.** AMI models, native FMUs, emulators, Verilator, ngspice, vendor engines, robot simulators and firmware toolchains run on Linux untrusted-evaluation workers, egress denied unless granted (contract section 7.8). Clients reach them remotely; air-gapped installs need a local Linux worker.
- **Emulator and simulator packages.** Renode has no ARM64 Linux package (D-ELX-18). MuJoCo's prebuilt binaries cover Linux on x86-64 and AArch64, Windows on x86-64, and macOS [24].
- **`f64` paths.** Analog analyses need `f64`, which Metal and WebGPU lack, so they run on CPU SIMD lanes everywhere. A server GPU class with Vulkan `SHADER_F64` may batch Monte Carlo at `Interactive` (contract section 7.5).
- **Browser memory.** DRC, fills and analyses estimated above 512 MiB run in the disposable heavy worker (PLT's browser memory table); larger boards go remote.
- **GPU placement.** The placer's FFT and gradient kernels go through `crucible:ops/flux` with CPU paths; placement is an edit, so class differences never reach an evaluation.
- **Hardware access.** Bench adapters and `flash_device` writes use USB and serial through `apps/platform`. Browsers use WebUSB and Web Serial, which MDN marks as limited availability [77][78]; elsewhere a local adapter program connects to `api`.
- **Accessibility.** Schematics, netlists, rules and DRC results are AccessKit trees, so a screen-reader user can capture and review a whole design as code.

## Interfaces with other subsystems

| To | ELX provides | Types |
| --- | --- | --- |
| ING | Builder semantics for `network { … }`; `Schematic` and `Layout` table rows and the layout fixture (D-ELX-27) | `Network`, `Feature` |
| FLX | The `network { … }` builder, port types and element libraries, the Verilog-A front end, board excitations and layered-sheet geometry | `Network`, `Field` |
| ANV | Planar workloads with centre-radius arcs for `anvil-planar`; bend lines for `anvil::fold` | `Body` |
| KLN and `repo` | Net partitions for the connectivity merge condition; `bare_board_invariant` and the covering-set policy; Software item definitions and `load` bindings; lifecycle placeholders | `Network`, `Part` |
| MEC | Bare and assembled boards (flat and folded), connector `CoordSys` values, harness connectivity and wire data, lumped motor and drive elements | `Part`, `Assembly`, `Network` |
| MFG | The board model with stackup, classes, footprints, test points, via protection and coating; the DRC engine for MFG's rule packs; harness data; DFM findings on board objects | `Part`, `Network` |
| COV | Equivalent-circuit and SPMe cells, swelling and abuse mechanics (contract section 13.4); packs | `Material`, `Field` |
| UIX | Canvas buffers for schematic, layout and constraint views; rule declarations; `schematic_matches_network`; recorded sessions for UIX-O-ELX-1 | `crucible:ui/canvas2d` buffers |
| AGT | Std features with doc metadata; GP5 electronics checks; Proposals from placement, routing, matching and decoupling tools; `flash_device` plans with Network hazards | `CheckOutcome`, Proposal |
| ECO | The board, netlist and library models; the electrical semantics of IDX, IPC-2581, ODB++, IPC-D-356, KiCad, harness, robot and systems formats; `CatalogSelection` | `Network`, `Part` |

| From | ELX requires |
| --- | --- |
| ING | `network { … }` with set-like accumulation; type-checked power expressions; `#[configuration]`; `#[interface]`; `Tol` correlation groups; `CatalogSelection` re-resolution; `#[waive]` as a Waiver request; `table { … }` rows read by the row lexer |
| ANV | `anvil::planar::boolean`, `offset`, `distance` and `medial_axis` with centre-radius arcs and conservative snapping; `anvil::fold`; `anvil::convex_decompose`; `anvil::text_outline` |
| FLX | `compile_network` and `solve_dae` with adjoint-weighted temporal estimates; block-triangular LU in `linalg`; layered-sheet, quasi-static, magnetostatic, eddy-current and full-wave solvers; conjugate heat transfer; parameter-domain forms; `flux::linearize_multibody`; `fft_solve`; the FMI and SSP runtime; Verilog-A in the kernel IR |
| KLN and `repo` | The connectivity merge condition; variant semantics, the 150% BOM and KLN-O-PLM-5; `Purchased` Items and the parts policy; `ItemDefinition` per Item kind; `OpCx::rng`; override keys; untrusted-evaluation workers with execution receipts; the evidence watermark |
| MEC | Enclosure geometry, keep-ins and connector frames; joints, mates and gear records; harness routes, bundle and formboard geometry; fastener selection under the parts policy |
| MFG | Rule packs per class, Class 1 included; output packages with IPC-D-356; panels, stencils and test programs; DFX feedback; the harness manufacturing package |
| COV | Dielectric, copper, magnetic and cell Materials with envelopes; physics models for EMC, thermal and cells; precision classes (D-COV-23) |
| UIX | The Electronics preset; schematic, layout and constraint canvases (D-UIX-27); waveform, Bode, Smith and eye charts; UIX-O-ELX-1 |
| AGT | `edit.stream` and `edit.apply`; the `flash_device` Act and its approval page; datasheet extraction with page references; Proposals under a `Budget` |
| ECO | Catalog service, `parts::` publishing with data licences (D-ECO-18) and the offer schema; every `io/` reader and writer with its phase |
| PLT | `detmath`; the `Interactive` pool lane; the browser memory table; USB and serial in `apps/platform`; registry font packages (D-PLT-7) |

ECO's format catalog owns the versions, exchange levels and phases of ELX's formats. KiCad's IPC API (Protocol Buffers over NNG [64]) serves as a live bridge for teams keeping some boards in KiCad during migration.

## Oracles

ELX oracles live in `oracles/elx/`; held-out sets are never shown to agents, and loosening a tolerance needs human approval.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ELX-O-EXT-1 | Port types, element libraries and analyses defined in a user namespace | Compile and evaluate identically to their std equivalents |
| ELX-O-NET-1 | Network builder and hierarchy | Connect order never changes the net partition; hierarchical golden designs flatten to known netlists |
| ELX-O-NET-2 | Net ties and connectivity merges | Every seeded net-merging branch pair reported as `Conflict::NetMerge`; non-overlapping pairs merge clean; every untied named-net join fails |
| ELX-O-NET-3 | Port types and element stamps | Every std port's power expression type-checks and seeded wrong ones fail; RLC, motor and drivetrain cases match analytic solutions |
| ELX-O-VAR-1 | Variant covering set and bare board | Every listed sellable configuration and the pairwise covering set build; a seeded footprint-changing variant fails `bare_board_invariant` |
| ELX-O-SCH-1 | Drawn schematics | In 10⁵ random view and code edits, view edits never change connectivity and no drawn group spans two nets after any code edit |
| ELX-O-SCH-2 | ERC | 100% recall on 300 human-labelled seeded schematics and a held-out 100; zero false positives on clean designs; an unsigned `#[waive]` never passes |
| ELX-O-SCH-3 | Netlists, schematic import and migration | Re-import equality; migrated designs' netlists equal the source tool's own netlist export |
| ELX-O-SCH-4 | Drawing output | Visual regression against stored references; placeholders filled only at output |
| ELX-O-SCH-5 | Data modules at scale | The 10⁶-row layout fixture parses and hashes in under 1 s natively (target); a region split rebuilds identically |
| ELX-O-CAT-1 | Facets, symbols and consistency checks | Every seeded inconsistent record blocked with the right `CatalogError` |
| ELX-O-CAT-2 | Footprint generators | Pad geometry within ±1 µm of an independent calculation on 2,000 packages |
| ELX-O-CAT-3 | Selections and offers | Identical pins give identical parts everywhere; argument changes re-resolve before release; update diffs list every substitution; a post-release offer refresh leaves the assembly BOM unchanged |
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
| ELX-O-LAY-4 | Autorouting | PCBWorld-Bench metrics [30] against Freerouting [35]; no Proposal with DRC errors |
| ELX-O-LAY-5 | Automatic placement | Cypress open suite [5] and held-out boards; targets in State of the art |
| ELX-O-LAY-6 | Rules, functional spacing and isolation barriers | Precedence property tests; IPC-2221 spacing reproduced per category and voltage; worked examples from each supported safety standard reproduced |
| ELX-O-LAY-7 | Test points and coating | Coverage recomputed from the netlist; every net without access receives a proposed test point or a stated reason; coated probe sites fail access |
| ELX-O-SI-1 | Impedance, RLGC, extraction and delay | ±1% against conformal-mapping solutions; ±10% against measured GP5 coupons (target) |
| ELX-O-SI-2 | Macromodels | Fit error under the stated bound; passive after enforcement by an independent Hamiltonian check |
| ELX-O-SI-3 | IBIS and channels | IBISCHK8 parse agreement [20]; vendor AMI examples reproduced; a forged receipt or two differing runs never pass a `SignOff` check |
| ELX-O-PI-1 | PDN, decoupling and IR drop | Analytic cavity resonances ±2%; analytic strip and annulus resistances ±1%; exact optimum on small decoupling instances |
| ELX-O-PI-2 | Electro-thermal coupling | Analytic self-heating of a uniform strip; `Runaway` reported at the turning point under current drive |
| ELX-O-EMC-1 | EMC screening | Analytic small-loop and short-dipole radiation; seeded rule and coupling cases; GP6 chamber scans as screening references |
| ELX-O-TH-1 | Board thermal | Layered model within its stated bound of explicit 3D copper on zoom cases; GP5 thermocouples ±5 K (target) |
| ELX-O-SIM-1 | Analog analyses | ngspice regression corpus run as an External Op and textbook circuits, relative 10⁻³ or absolute 1 µV; an LC oscillator's transient reports `Indicator` temporal error without the adjoint or step-halving estimate |
| ELX-O-SIM-2 | Vendor models | At least 95% of the unencrypted vendor corpus parses, converges and matches the vendor's reference engine within 1% (target) |
| ELX-O-SIM-3 | Verilog-A compact models | I-V and C-V curves against OpenVAF-compiled references run as External Ops, relative 10⁻⁶ |
| ELX-O-SIM-4 | Monte Carlo, sensitivity and worst case | Identical samples in every class and under re-randomized names; added samples leave earlier ones unchanged; adjoint sensitivities pass Taylor tests |
| ELX-O-SIM-5 | Mixed-signal | Event times within one analog step of ngspice XSPICE references |
| ELX-O-REL-1 | Reliability and derating | Handbook worked examples to printed precision [58][59]; physics-of-failure models against their cited datasets |
| ELX-O-MCH-1 | Machines | Analytic slotless fields and winding factors, torque ±3%; TEAM problem 30a [81]; GP6 dynamometer efficiency ±5 points (target) |
| ELX-O-MCH-2 | Actuators, sensors and drives | Analytic solenoid force; datasheet transfer curves; averaged-model cases against ngspice |
| ELX-O-CTL-1 | Control design and code generation | Closed-form Riccati, margin and reduction-bound cases to relative 10⁻⁹; Maros-Meszaros QPs to their reference objectives [102]; generated code bit-exact with the Ingot reference |
| ELX-O-CTL-2 | FMU elements and bus simulation | Reference FMUs map ports and units correctly; the FMI-LS-BUS demo FMUs for CAN and FlexRay [80] exchange their frames |
| ELX-O-FW-1 | Firmware-in-the-loop | Reference firmware traces identical across repeated runs per class and per Renode release; PWM-to-RC timing error within the reported bound |
| ELX-O-FW-2 | Hardware-in-the-loop | Fixed-step exports bit-exact with the reference; evidence on an incompatible version never counts; two Evaluations at one evidence watermark agree |
| ELX-O-FW-3 | Firmware flashing | Every client path, WebUSB included, flashes through `flash_device`; targets stay in reset until released at the bench; a read-back mismatch fails the Act; rotational ports add the propellers step |
| ELX-O-BAT-1 | Cell models | 1 mV RMS against PyBaMM on shared parameter sets (target); analytic diffusion; fitted parameters recover known values; fitted LFP hysteresis reproduces measured loops |
| ELX-O-BAT-2 | Packs and swelling | Hand-computed pack resistance and capacity; analytic busbar resistance; swelling against PyBaMM's swelling model; GP6 pack voltage under 30 mV RMS per cell (target) |
| ELX-O-BAT-3 | Pack safety and abuse | Published coordination examples; abuse screening against the jellyroll model's calibration data and GP12 crush tests |
| ELX-O-PWR-1 | Converters | Textbook steady-state and averaged-model cases; analytic loop inductance; GP6 calorimetric efficiency |
| ELX-O-PWR-2 | Magnetics | MagNet metric no worse than the iGSE baseline [39]; Dowell analytic cases [100] |
| ELX-O-HAR-1 | Harness | Hand-checked golden harness wire table, lengths and checks; package contents complete |
| ELX-O-HAR-2 | VEC and KBL | Schema validation and round trip with zero dropped elements |
| ELX-O-ROB-1 | Robot exports | Mass properties equal Anvil's to relative 10⁻⁹; files load in MuJoCo and Gazebo without warnings; sdformat_mjcf round trip [25] |
| ELX-O-ROB-2 | Trajectories and planning hooks | Analytic single-joint cases; recorded planner sessions |
| ELX-O-RF-1 | Antennas | Dipole impedance against Hallén's integral equation for the modelled radius; cavity-model patch; Palace cross-check, ±2% resonance |
| ELX-O-RF-2 | Matching and linear RF | Analytic L-networks to 10⁻⁶; Bode-Fano bound never exceeded; textbook amplifier cases |
| ELX-O-SYS-1 | System model and status | Resolution tests; seeded status corpus |
| ELX-O-SYS-2 | SysML v2 and ReqIF | Round trip of the pilot implementation's examples [31] and sample ReqIF files with no dropped elements |
| ELX-O-SYS-3 | Software items | Seeded board-description mismatches all fail; reference firmware rebuilds to identical hashes; a binary swap after approval voids the Approval |
| ELX-O-DET-1 | Determinism and label invariance | Golden boards hash identically on every Tier 1 platform; re-randomized names and designators leave copper and check values identical |

## Phasing

Shared capabilities take their phase from contract section 13.4: conjugate heat transfer, electro-thermal coupling, FMU export and SSP, and every battery cell row. No ELX row precedes an owner's row that it names.

| Phase | ELX contribution to the gate |
| --- | --- |
| 0 | None |
| 1 | No gate contribution. The circuit-simulation research track prototypes the modified-nodal-analysis engine, assembles the vendor-model corpus and settles the Verilog-A front end's scope |
| 2 | GP3: the `network { … }` builder, rotational, translational and thermal ports, drivetrain elements and `CatalogSelection` over pinned definitions. ECO's IDF, STEP board and IDX baseline import serve enclosure design; ING measures ELX's layout fixture (D-ELX-27) |
| 3 | GP5, its board fabricated and assembled from Crucible outputs alone, through the phase 3 rows above. Evidence: DRC and ERC clean; the fabricator's DFM with zero errors; coupon impedance within ±10% and hottest part within ±5 K of measurement (targets); board data identical on every Tier 1 platform |
| 4 | GP6, through the phase 4 rows above. Evidence (targets): hover endurance ±10% of flight test; motor efficiency ±5 points; pack voltage under 30 mV RMS per cell; attitude-loop overshoot and settling ±20%; antenna resonance ±2% |
| 5 | GP7: the MEMS reduced-order model as a Network element for readout simulation. The other phase 5 rows serve no gate |
| 6 | GP11 CubeSat: board, harness and firmware flows. GP12 battery sub-pack with BMS, harness and charger: pack safety, abuse mechanics, pack-scale DFN, high-voltage barriers |
| 7 | None |

## Open questions

1. **Verilog-A front end.** The phase 1 research track decides whether a clean-room front end fits phase 3; the fallback is ported SPICE3 models with ngspice vendor models. Only the track's prototype can measure that scope.
2. **GPU back ends (R1-39, declined in part).** CUDA and ROCm wait for the phase 4 gate decision in contract section 7.5. Vulkan `SHADER_F64` server classes serve until then.
3. **R10-45, applied in part.** Layouts stay text as it asks, but a region split replaces its binary-sidecar fallback, following R9-34 (D-ELX-27).

## Contract change requests

None. CCR-ELX-8, the battery swelling and abuse rows, was accepted in contract v5 (section 13.4).

## Sources

Pages opened with WebFetch in October 2026; [65] to [69] were opened in round 2 and [70] to [104] in round 3. Vendor performance claims are reported as the vendors state them.

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
- [70] PyBaMM documentation, `OneStateHysteresisOpenCircuitPotential` (after Börjesson Axén et al., Journal of Energy Storage 48, 2022). https://docs.pybamm.org/en/latest/source/api/models/submodels/interface/open_circuit_potential/one_state_hysteresis_ocp.html
- [71] PyBaMM documentation, `SwellingOnly` (after Ai, Kraft, Sturm, Jossen and Wu, J. Electrochem. Soc. 167(1) 013512). https://docs.pybamm.org/en/latest/source/api/models/submodels/particle_mechanics/swelling_only.html
- [72] Crossref record: Wierzbicki and Sahraei, "Homogenized mechanical properties for the jellyroll of cylindrical Lithium-ion cells", Journal of Power Sources 241 (2013) 467–476. https://api.crossref.org/works/10.1016/j.jpowsour.2013.04.135
- [73] prostep ivip ECAD wiki, KBL specifications (KBL 2.5 SR-1). https://ecad-wiki.prostep.org/specifications/kbl/
- [74] ECSS, ECSS-Q-ST-30-11C Rev.2, "Derating – EEE components", 23 June 2021. https://ecss.nl/standard/ecss-q-st-30-11c-rev-2-derating-eee-components-23-june-2021/
- [75] SDFormat specification page (versions 1.4 to 1.12). http://sdformat.org/spec
- [76] ROS REP 2000, "ROS 2 Releases and Target Platforms". https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-2000.rst
- [77] MDN Web Docs, WebUSB API. https://developer.mozilla.org/en-US/docs/Web/API/WebUSB_API
- [78] MDN Web Docs, Web Serial API. https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API
- [79] Renode documentation, "Writing peripherals" (SystemRDL stubs through peakrdl-renode; SVD register tags). https://renode.readthedocs.io/en/latest/advanced/writing-peripherals.html
- [80] Modelica Association, FMI-LS-BUS examples repository (demo FMUs for CAN and FlexRay). https://github.com/modelica/fmi-ls-bus-examples
- [81] International Compumag Society, TEAM problems. https://www.compumag.org/wp/team/
- [82] SPDX, specifications page (SPDX 3.0; ISO/IEC 5962:2021). https://spdx.dev/use/specifications/
- [83] CycloneDX, specification overview (1.7, 21 October 2025; ECMA-424). https://cyclonedx.org/specification/overview/
- [84] NIST, NISTIR 7648, "Representation of a Thermal Resistor Network Model of a Packaged Component in STEP AP210 Edition 2" (JESD15-3 two-resistor and JESD15-4 DELPHI models). https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7648.pdf
- [85] Global Electronics Association, "Meet Your Standards" (IPC-6012F, IPC-A-610J, IPC J-STD-001J, IPC-4101E-WAM1, IPC/WHMA-A-620F). https://www.electronics.org/meet-your-standards
- [86] IPC, "IPC Releases 'J' Revisions to Two Leading Standards for Electronics Assembly", 8 April 2024. https://www.electronics.org/news-release/ipc-releases-j-revisions-two-leading-standards-electronics-assembly
- [87] Global Electronics Association, "Building Electronics Better Using Design Standards" (IPC-2152, IPC-2221C, IPC-2223E, IPC-2581C, IPC-7351B, IPC-7352, IPC-D-356B). https://www.electronics.org/ipc-design-standards
- [88] Altair Pollex help, "IPC Material" (conductor-spacing categories B1 to A7 of Table 6-1). https://help.altair.com/pollex/topics/pollex/verification/dfe_ipc_material_r.htm
- [89] LEITON, via plugging, tenting and filling to IPC-4761 (types I to VII). https://www.leiton.de/special-technologies-via-plugging-tenting-filling-ipc-4761.html
- [90] EVS, IEC 62368-1:2023. https://evs.ee/en/iec-62368-1-2023
- [91] EVS, IEC 61010-1:2010 with AMD1:2016. https://www.evs.ee/en/iec-61010-1-2010
- [92] EVS, IEC 60601-1:2005 with AMD1:2012 and AMD2:2020. https://www.evs.ee/en/iec-60601-1-2005
- [93] IEC webstore, IEC 60617:2026 DB, graphical symbols for diagrams. https://webstore.iec.ch/en/publication/2723
- [94] IEEE SA, IEEE 315-1975, inactive-reserved since 7 November 2019. https://standards.ieee.org/ieee/315/515/
- [95] Wikipedia, "EDIF". https://en.wikipedia.org/wiki/EDIF
- [96] UW CSE News, "CSE's Carl Ebeling wins 'Top 25 in 20' from FPGA" (PathFinder, McMurchie and Ebeling, FPGA 1995), 1 March 2012. https://news.cs.washington.edu/2012/03/01/cses-carl-ebeling-wins-top-25-in-20-from-fpga
- [97] Crossref record: Grivet-Talocia, "Passivity Enforcement via Perturbation of Hamiltonian Matrices", IEEE Trans. Circuits and Systems I 51(9) (2004) 1755–1769. https://api.crossref.org/works/10.1109/tcsi.2004.834527
- [98] Crossref record: Middlebrook, "Measurement of loop gain in feedback systems", International Journal of Electronics 38(4) (1975) 485–512. https://api.crossref.org/works/10.1080/00207217508920421
- [99] Crossref record: Tian, Visvanathan, Hantgan and Kundert, "Striving for small-signal stability", IEEE Circuits and Devices Magazine 17(1) (2001) 31–41. https://api.crossref.org/works/10.1109/101.900125
- [100] Crossref record: Dowell, "Effects of eddy currents in transformer windings", Proceedings of the IEE 113(8) (1966) 1387. https://api.crossref.org/works/10.1049/piee.1966.0236
- [101] IEEE P802.3ck, tools and channel data page (contributed channels; COM). https://www.ieee802.org/3/ck/public/tools/index.html
- [102] qpbenchmark, Maros-Meszaros test set (138 convex quadratic programs). https://github.com/qpsolvers/maros_meszaros_qpbenchmark
- [103] Optenni, Optenni Lab. https://www.optenni.com/optenni-lab/
- [104] KiCad, library licence (CC-BY-SA 4.0 with a design exception). https://www.kicad.org/libraries/license/
