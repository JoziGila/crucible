# Electronics, mechatronics and system modeling

Electrical intent in Crucible is a typed Ingot program. Circuits are code with stored schematic views, boards are Parts whose copper is versioned data, and every analysis returns Fields and Checks with a stated validity envelope. One model holds schematic, layout, enclosure, firmware, harness and requirements, so nothing needs a sync step.

## Scope

This tab (code ELX) owns electrical connectivity, catalog-part electrical data, schematic capture, PCB layout, electrical analyses, mechatronic and power models, control design, co-simulation, harness connectivity, robot description export and requirements traceability. It consumes geometry from Anvil, physics solvers from Flux, assemblies and motion from Mechanical (MEC), and process capability from Manufacturing (MFG).

Out of scope, stated plainly:

- Integrated-circuit and FPGA internals (die layout, synthesis, FPGA place-and-route). Chips are modeled only through catalog-part models: pins, SPICE, Verilog-A, IBIS and thermal data.
- Regulatory verdicts. No simulator can certify EMC, safety or radio compliance; Crucible produces screening results and evidence for a test lab, never a pass verdict.
- Real-time guarantees. Hardware-in-the-loop runs outside Kiln's deterministic evaluation (see "Hardware-in-the-loop").
- Semiconductor device physics below compact models (TCAD), arc and plasma physics in contactors and fuses, and electrochemistry below porous-electrode theory. Published compact, behavioral or empirical models stand in for them, each with its envelope stated.
- Field-life forecasts. Reliability handbooks give comparative failure rates, not predictions of when a given unit fails.

### Extending the electrical model

New physics enters through the contract's public mechanisms, never through privileged code:

1. **A new lumped domain** (for example acoustic or pneumatic) is an Ingot package that declares a port type with its across and through quantities as `Quantity` dimensions. The network compiler and DAE solver then accept it (D-ELX-15).
2. **A new device model** is Verilog-A (D-ELX-14) or an Ingot equation element, published as a package with its `ValidityEnvelope` and oracle cases.
3. **A new analysis** is an Ingot feature over Flux forms, or a Wasm component for heavy custom algorithms, and returns Fields and Checks.
4. **A new exchange format** is an `io/` Wasm component with round-trip oracles.
5. **Promotion.** Logic that proves hot or general moves to a Flux operation with oracles, as the contract's promotion path requires.

## The electrical model

### Types

`std::elx` adds domain types, all built from the core types. None is a third universal type: circuits and stackups are plain values, geometry stays in Bodies and physics results stay in Fields.

| Type | What it is | Relation to core types |
| --- | --- | --- |
| `Circuit` | Hierarchical connectivity: catalog-part Instances, sub-circuit occurrences, nets, ports | Plain value; its leaf elements are Instances |
| `Net` | One electrical node with a name, net class and properties | Plain value inside a `Circuit` |
| `Pin` | A terminal of a catalog part, with electrical type and alternate functions | Facet of a catalog part |
| `Port` | A typed connection point on a `Circuit`. Compound port types (`Power`, `I2c`, `Spi`, `UsbC`, `Can`) group sub-ports with roles | Ingot struct type with role annotations |
| `Schematic` | Drawing annotations for one `Circuit`: pages, symbol positions, wire paths, labels, notes, reference designators | Data module; a view, never a source of connectivity |
| `Stackup` | Ordered layers with Materials, `Tol<Length>` thicknesses, via spans and rigid-flex zones | Plain value referencing Materials |
| `Layout` | Designer-authored placements, tracks, arcs, vias, zones and keepouts | Data module; placements are Instance `Transform`s |
| `Footprint` | Padstacks plus mask, paste, silkscreen, courtyard and fabrication layers, with a pad-to-pin map | Data in integer coordinates, like `Layout` (D-ELX-6); Bodies derived |
| Bare board | The printed board | A Part of kind `pcb`, Body derived from `Stackup` and outline |
| Assembled board | Bare board plus catalog-part Instances | An Assembly |
| Design rule | Clearance, width, impedance, delay match and so on | A Check built by a `std::elx::rules` constructor |
| Waveform, spectrum, trajectory | Response over time or frequency | `Field<TimeSpan, V>` or `Field<FreqSpan, V>` (CCR-1) |

**Decision D-ELX-1:** Connectivity is Ingot code; a schematic is a stored view of that code. The visual editor writes `connect` statements to the circuit source and drawing annotations to a `Schematic` data module beside it. *Why:* agents and the code editor need text connectivity (principle 2); connectivity then diffs and merges semantically, and the compiler type-checks compound ports, voltage domains and pin types before anything runs. Reviewers still get a conventional drawn schematic. *Rejected:* drawing-as-source (KiCad, Altium), because connectivity derived from wire geometry cannot be merged or edited safely by agents and breaks on near-miss wires; code-only capture with automatically generated drawings, because generated drawings of large designs lose the signal-flow layout that review depends on. atopile shows that code capture with units, tolerances and automatic part picking works in practice [4]; Crucible adds the stored drawn view.

**Decision D-ELX-2:** Every occurrence of a catalog part in a circuit is an Instance of the Part that the catalog record defines. The bare board is a Part, and the assembled board is an Assembly whose Instance placements are the footprint placements. Sub-circuit occurrences are hierarchy nodes of the `Circuit`; they add Assembly levels only when the designer declares a sub-assembly, such as a daughterboard. *Why:* one BOM query (`repo`) covers mechanical and electrical items, and moving a part in layout is the same edit as moving it in the assembly. *Rejected:* a separate "component" or "symbol instance" concept, which would duplicate Instance and need a sync step.

[[DIAGRAM: Electrical source model. Authored boxes: circuit source (.ingot), Schematic module, Layout module, Stackup, lockfile-pinned catalog-part records. Derived boxes: Circuit value, copper and laminate Bodies, bare-board Part, assembled-board Assembly, product Assembly with the enclosure from MEC. Arrows: schematic editor writes circuit source and Schematic; layout editor writes Layout; code editor and agents write all three; Kiln builds Circuit from source; Circuit, Layout and Stackup produce derived Bodies, then the Part, then the Assembly with catalog-part bodies; enclosure geometry flows back into outline and locked placements as expressions.]]

### Writing a circuit

```
use std::elx::{Circuit, Power, net, connect, resistor, capacitor, inductor}
use parts::ti::tps62130                  // catalog part package, pinned in the lockfile (illustrative)

pub feature buck_3v3(vin: Power, load: Current = 2A) -> Circuit {
    let c = circuit {
        let u1   = tps62130()
        let l1   = inductor(1uH ± 20%, i_sat_min: 1.5 * load)   // parametric pick
        let c_o  = capacitor(47uF ± 20%, v_rated_min: 10V, dielectric: x7r)
        let r_hi = resistor(100kohm ± 1%)
        let r_lo = resistor(31.6kohm ± 1%)
        let out  = net("3V3")

        connect(vin.pos, u1.pin("PVIN"), u1.pin("AVIN"))
        connect(u1.pin("SW"), l1.a)
        connect(l1.b, out, c_o.a, r_hi.a)
        connect(r_hi.b, r_lo.a, u1.pin("FB"))
        connect(vin.neg, u1.pin("PGND"), c_o.b, r_lo.b)
        port vout = Power(out, vin.neg, range: 3.3V ± 2%)
    }
    c.require(dc_voltage(c.vout) in 3.3V ± 2%)
     .require(ripple_pp(c.vout, load: load) < 20mV)
}
```

The `circuit { … }` block is a builder, like `sketch(plane.xy) { … }`: `connect` statements accumulate into one value, and connecting the same pins twice is idempotent. Port-typed feature parameters such as `vin` become boundary ports, and `port` declares new ones. The block returns a `Circuit`; nothing outside it can mutate connectivity.

The editor stores drawing intent separately, in canonical form with one item per line and stable ids:

```
// buck_3v3.schematic.ingot — written by the schematic editor
schematic buck_3v3 {
    frame a4
    symbol u1  at (60mm, 40mm) rot 0deg  unit A
    symbol l1  at (90mm, 40mm) rot 0deg
    wire   w_3c1 [u1.pin("SW"), l1.a] path [(78mm, 40mm)]
    label  out at (110mm, 40mm)
    note   n_01 at (20mm, 120mm) "Keep SW node area small"
}
```

Editor behavior follows from D-ELX-1:

1. Drawing a wire between two pins adds them to one `connect` statement and stores the wire path. A wire end that touches no pin is impossible: the editor snaps or refuses.
2. A connection added in code but not drawn appears as a dashed "undrawn connection". One action draws it with the orthogonal router, or places a net label.
3. Annotations that point at removed pins fail with `SchematicError::StaleAnnotation` and a one-click fix. They never change connectivity.
4. Moving a symbol edits only the `Schematic` module. Two branches that move different symbols merge cleanly; moving the same symbol is a typed merge conflict.
5. A drawn connection is written into the `circuit` block that owns both pins. A wire that crosses a hierarchy boundary adds a port to the sub-circuit and asks for its name.
6. Connectivity generated by code, such as a loop over channels, is read-only in the drawing. Editing it opens the generating source line instead of writing a special case.

Every `Circuit` has a `Schematic` module, even one captured only in code; such a module may hold only reference designators.

### Catalog-part selection

**Decision D-ELX-3:** A circuit element names either an exact catalog part or a parametric selection, which is a `Query` over the catalog. Selections resolve when the lockfile is created or updated, like package versions, and builds read the pinned result. *Why:* designers state intent (`1uH ± 20%`, saturation current above 3 A) while builds stay deterministic; `crucible update parts` re-resolves on demand and the diff shows each substitution. *Rejected:* re-resolving on every build, which makes builds depend on supplier data; exact-only selection, which loses intent and blocks automatic second sourcing.

A selection that matches nothing fails with `ResolveError::NoCatalogMatch`, naming the tightest constraint and the nearest candidates. A selection never widens its own constraints.

### Hierarchy, buses and ports

- **Hierarchy.** A sub-circuit is a feature that returns a `Circuit`; using it creates an occurrence with ports. Repeated channels use ordinary loops. Each occurrence gets its own `Schematic`, or several share one drawing with per-channel reference designators.
- **Pages.** A `Schematic` may span several pages. Off-page connections are net labels with automatic cross-references (page and zone), generated from connectivity rather than typed by hand.
- **Reference designators.** Designators are stored in the `Schematic` module and stay stable across edits. Renumbering is an explicit command whose result is a reviewable diff. The default scheme is position-ordered per page (`R1`…), with channel suffixes for repeated blocks.
- **Buses.** A bus is a compound `Port` or a vector of nets (`Bus<8>`). Connecting two compound ports checks roles: `I2c.scl` to `I2c.scl`, one controller to many targets, compatible directions. Joining incompatible ports is a compile error that suggests the adapter part, such as a level shifter.
- **Global nets.** Implicit global nets do not exist. Power and ground travel through `Power` ports; a design may declare `global net GND` once at the top level, and every use is visible in the source.
- **Electrical typing.** `Power` carries a voltage range as `Tol<Voltage>`. Pins carry absolute-maximum and recommended ranges from catalog data. Static mismatches fail at compile time; value-dependent ones become checks.

### Variants

**Decision D-ELX-4:** A variant is a value of the design's `Variant` parameter. Fitted state, part choice and part values are ordinary expressions of it. Every declared variant builds and passes its checks in CI. *Why:* variants then reuse Kiln parameterization, caching and checks, with no parallel table to drift. KiCad 10 ships design variants that share a schematic and differ in properties such as the BOM [1]; Crucible covers that case and also lets variants change rules and analyses. *Rejected:* variant tables stored beside the design, a second mechanism with its own merge semantics.

```
let r_term = resistor(120ohm ± 1%).fitted(variant != Variant.lite)
let u_rf   = match variant { Variant.eu => parts::nordic::nrf9161(), _ => parts::nordic::nrf9151() }
```

The UI shows a variant matrix generated from these expressions where they are simple `fitted` or `match` forms. Each variant has its own BOM view (EBOM and MBOM through `repo`) and its own assembly outputs. Unfitted parts render with a cross in the schematic and drop out of pick-and-place.

## Catalog parts

### The electrical facets of a catalog part

A catalog part is one record in the parts catalog. This tab specifies its electrical facets; the catalog service, the registry and supplier integrations belong to the Ecosystem tab (ECO), and mechanical facets of fasteners and bearings belong to Mechanical (MEC). Every facet is versioned with the record, and a design pins the record version in its lockfile.

| Facet | Contents | Typed as |
| --- | --- | --- |
| Identity | Manufacturer, part number, lifecycle state, package code, compliance declarations | Plain values |
| Pins | Number, name, electrical type, alternate functions, swap groups, pin groups, absolute-maximum and recommended ranges | `Pin` records with `Tol<Voltage>`, `Current` |
| Symbols | One or more symbol bodies, multi-unit gates, alternate body styles, pin placement | Ingot data module |
| Footprints | One or more land patterns per package and density level, pad-to-pin map, courtyard | `Footprint` built by a generator feature or stored data |
| 3D body | Exact body from the manufacturer's STEP, a simplified envelope Body and a keep-out Body | `Body` (BRep), imported once and stored in CAS |
| Specifications | Parametric values: capacitance, voltage rating, saturation current, θJA and so on | `Quantity<D>` and `Tol<T>` with test conditions |
| Simulation models | SPICE subcircuits, Verilog-A source, IBIS, IBIS-AMI, Touchstone, thermal compact models, magnetics records | Typed model references with a `ValidityEnvelope` each |
| Reliability | Base failure-rate category, stress parameters, derating curves | Plain values and curves |
| Design rules | Required decoupling, layout rules from the datasheet, strap pins, exposed-pad rules | Checks attached to the part |
| Supplier data | Offers, stock, price breaks, lead time | Snapshot, outside deterministic builds |

**Decision D-ELX-5:** Supplier data never enters evaluation. Builds read only the catalog record version pinned in the lockfile; price, stock and lead time come from a dated snapshot that the BOM view reads and labels with its date. *Why:* stock levels change hourly, and determinism (principle 4) forbids a build that depends on them. *Rejected:* live supplier lookups during builds.

### Footprints from data

Land patterns follow IPC-7351B, whose 2010 edition is still the active revision [55][56]. It defines three density levels per package, and the 2010 revision added DFN families, default paste for thermal pads and a padstack naming convention [55].

Crucible ships footprint generators as Ingot features (`std::elx::footprint::qfn`, `soic`, `bga`, `chip`, `sot`), driven by package dimensions with tolerances. KiCad reports that over 78% of its footprints are now generated from data [1]; Crucible's target is 100% for standard packages, with stored data reserved for irregular parts such as connectors and modules.

```
let fp = footprint::qfn(
    body: (4mm ± 0.1mm, 4mm ± 0.1mm), pitch: 0.5mm, pins: 24,
    lead_len: 0.4mm ± 0.05mm, exposed_pad: (2.6mm, 2.6mm),
    density: Density.nominal,                    // IPC-7351B level
)
.require(paste_coverage(fp.exposed_pad) in 50% .. 80%)
```

Each generator computes toe, heel and side fillets from the tolerance stack, so pads respond to `Tol` widths. The pad-to-pin map is checked against the symbol at build time (`CatalogError::PinPadMismatch`).

### Symbols

Symbols are generated from the pin table wherever possible: pins grouped by function (power left or top, ground bottom, inputs left, outputs right), multi-unit parts split by gate or by pin group, and power units separable for large parts. KiCad 10 added CSV import and export of symbol pin tables [1]; Crucible treats the pin table as the source and the drawn symbol as a generated view that a librarian may refine.

A symbol may carry alternate body styles, for example IEC 60617 and ANSI/IEEE 315 styles for logic and passives [unverified current editions], selected per design. Each symbol pin maps to exactly one catalog-part pin; a mismatch fails with `CatalogError::SymbolPinMismatch`.

### Creating catalog parts

1. **From a datasheet.** An agent extracts pins, package dimensions and specifications from the datasheet PDF into a new record and opens a Proposal. Every extracted value carries a reference to its page and table. A human approves the Proposal; extraction alone never publishes.
2. **From existing libraries.** Importers read KiCad libraries (open S-expression formats) as Wasm components. Proprietary library formats come only through licensed translator plugins, as the contract requires.
3. **By hand.** The symbol and footprint editors write the same Ingot data modules.

Automatic consistency checks run on every record:

- pin count equals pad count after mapping;
- the footprint courtyard encloses the 3D body's projection;
- pin electrical types agree with the IBIS model's pin list;
- the SPICE subcircuit's port order matches the pin map.
 Failures block publication with `CatalogError` values that name the facet and the mismatch.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Electrical facets | Versioned record with pins, symbols, footprints, 3D body, specifications, models, reliability data and rules | A missing facet blocks only the uses that need it: a part without IBIS data cannot enter SI, and the analysis says so | Facet schema validation | 3 |
| Footprint generators | Package dimensions with `Tol` to `Footprint` | Dimensions outside a generator's family are a typed error | Independent IPC-7351B calculation | 3 |
| Symbol generation | Pin table to symbol view | A pin without a placement rule is listed | Pin-map consistency tests | 3 |
| Datasheet extraction | PDF to a record Proposal with page references | Values without a source reference are rejected | Held-out datasheets with hand-entered records | 4 |
| Library import | KiCad libraries to records | Unmapped fields are listed | Round trip | 3 |
| Consistency checks | Agreement of pins, pads, symbol, models and body | `CatalogError` blocks publication | Seeded inconsistent records | 3 |
| Supplier snapshot | Dated offers for BOM views | A stale snapshot is labelled with its age | Snapshot replay | 3 |

## Schematic capture

### Capabilities

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Circuit as code | Ingot `circuit { … }` returns `Circuit`; `connect` is idempotent | Type errors at compile time with fixes, such as an adapter part | Compiler test suite; property test that connect order does not change the circuit hash | 3 |
| Stored schematic view | `Schematic` module holds positions, wire paths, labels, notes; never connectivity | `SchematicError::StaleAnnotation` with a one-click fix | Property test: 10⁵ random schematic-view edits leave the connectivity hash unchanged | 3 |
| Undrawn connections | Code-only connections render dashed until drawn | None; informational marker | UI test corpus | 3 |
| Hierarchy | Sub-circuits are features returning `Circuit`; repeated channels by loops | Port mismatch is a compile error | Hierarchical golden designs flatten to known netlists | 3 |
| Buses and compound ports | `Bus<N>` and compound `Port` types with roles | Role mismatch is a compile error | Seeded-error corpus | 3 |
| Reference designators | Stable, stored in `Schematic`; explicit renumber command | Duplicate designator is a build error | Uniqueness property test | 3 |
| Variants | `Variant` parameter; `fitted` and `match` expressions | Unbuildable variant fails CI with the variant name | Every declared variant built in CI | 3 |
| Parametric selection | Catalog `Query` pinned in the lockfile | `ResolveError::NoCatalogMatch` with nearest candidates | Resolution replay: identical lockfile gives identical parts | 3 |
| Pin and gate swap | Swap within catalog swap groups, from schematic or layout; one edit in source | Swap outside a group is refused | Swap round-trip tests | 3 |
| Design blocks | Reusable sub-circuit plus its layout fragment, published as a package | Layout fragment that cannot place is reported, schematic still applies | Block reuse golden tests | 4 |
| Netlist export | SPICE, KiCad netlist, EDIF 2 0 0 [unverified], IPC-D-356 (from layout) | Unsupported construct is listed, never dropped silently | Re-import comparison | 3 |
| Schematic import | KiCad schematics as a Wasm component: wire connectivity becomes circuit source, drawing becomes the `Schematic` module; others through licensed plugins | Unmapped objects and near-miss wires listed in an import report | Round trip on a corpus of open-source KiCad projects | 3 |
| Printing and PDF | Drawing output with title blocks and cross-references | None expected | Visual regression against stored references | 3 |

### Electrical rule checks

ERC is a set of checks in `std::elx::erc`, evaluated on every build. Kiln re-evaluates only the nets an edit touched. Each rule has a severity, an explanation and a suggested fix; a waiver is an Ingot statement with a reason and an author, so waivers appear in review diffs.

| Rule family | Examples | Source of truth |
| --- | --- | --- |
| Pin-type matrix | Two push-pull outputs on one net; input with no driver; power input with no source | Pin electrical types |
| Topology | Single-pin net; unconnected required pin; connected no-connect pin; floating sub-circuit port | `Circuit` |
| Voltage domains | Net voltage range outside a pin's absolute-maximum range; logic level mismatch | `Tol<Voltage>` on `Power` and pins |
| Power budget | Sum of worst-case load currents exceeds a regulator's rating; inrush beyond fuse rating | Catalog specifications |
| Bus semantics | I2C address collision; missing or duplicate pull-ups; SPI chip-select sharing | Compound port roles |
| Part rules | Missing decoupling capacitor required by the datasheet; strap pin left floating; exposed pad not connected | Catalog part design rules |
| Protection | External connector net without ESD protection; reverse-polarity exposure on a supply input | Port annotations (`external`) |
| Differential pairs | Polarity swapped across a hierarchy boundary; pair members in different net classes | Net class declarations |

Waived checks remain visible in the CI report. A waiver whose rule no longer fires produces a stale-waiver warning, so waivers cannot accumulate silently.

Oracle: a protected corpus of 300 schematics with seeded violations, labelled by humans. Target: 100% recall on seeded violations and zero false positives on the clean corpus.

## The board as a Part

### Stackup

A `Stackup` is an ordered list of layers plus the via spans the fabricator can build. Each dielectric layer references a Material whose permittivity and loss tangent are Fields over frequency, fitted with a causal wideband model (multi-pole Debye) so that time-domain analyses stay causal. Each copper layer carries weight, thickness as `Tol<Length>`, a roughness model and its role (signal, plane, mixed).

```
let stack = stackup(name: "6L-1.6mm") {
    copper(L1, 35um, role: signal)        prepreg(fab::it180a_2116, 0.11mm ± 10%)
    copper(L2, 35um, role: plane(GND))    core(fab::it180a_core, 0.71mm ± 10%)
    copper(L3, 35um, role: signal)        prepreg(fab::it180a_7628, 0.2mm ± 10%)
    copper(L4, 35um, role: signal)        core(fab::it180a_core, 0.2mm ± 10%)
    copper(L5, 35um, role: plane(PWR))    prepreg(fab::it180a_2116, 0.11mm ± 10%)
    copper(L6, 35um, role: signal)
    vias [through(L1, L6), blind(L1, L2, laser), buried(L3, L4)]
}
.require(total_thickness(stack) in 1.6mm ± 10%)
```

Fabricator materials come from Manufacturing's process capability records (`fab::…` above), so a stackup built from them inherits the fabricator's allowed thicknesses and via spans. A stackup that uses a span the fabricator cannot build fails with `StackupError::UnsupportedSpan`, which names the fabricator and the nearest supported span.

**Regions.** A board may hold several stackups, one per outline region: rigid zones, flex zones, cavities and stiffener areas. Region boundaries are curves on the board outline. Every layout item lies in a region, and DRC applies that region's layer set.

### Board geometry

**Decision D-ELX-6:** Authored layout geometry (tracks, arcs, pads, vias, zone outlines) is stored as data in 64-bit integer nanometre coordinates on a per-board frame, bounded to ±2^40 nm (about ±1.1 km). Arcs are stored as three integer points. Line predicates are exact in 128-bit integers; arc predicates use exact rational arithmetic, squaring both sides where a comparison involves a radius. Anvil Bodies are derived on demand: planar (zero-thickness) Bodies per copper layer, and solids for the laminate, copper and holes. *Why:* integer coordinates make DRC and fill bit-identical on every platform. A track segment stored as data costs tens of bytes; as a B-rep it would need faces, edges, vertices and their geometry. Deriving Bodies keeps one geometry type for every consumer (principle 3). *Rejected:* storing copper as B-rep Bodies, which is too heavy for interactive routing; floating-point layout coordinates, which make clearance decisions differ across platforms.

The relationship is the same as a sketch's: authored entities are data, and features turn them into Bodies.

| Derived Body | Representation | Consumers | Error bound |
| --- | --- | --- | --- |
| Laminate | BRep solid: outline extruded by stackup thickness, holes and cutouts subtracted | MEC fit and interference, Flux structural, STEP export | Exact |
| Copper layer *n* | Planar BRep at the layer's z, from tracks, pads and zone fills | DRC, Flux EM and conduction, Gerber, 3D view | Exact for lines and arcs; pour arcs within chord tolerance (default 0.5 µm, stated) |
| Copper solid | Planar copper extruded by copper thickness | Flux 3D EM, thermal sign-off | As above |
| Assembled board | Assembly of the laminate plus catalog-part 3D bodies at footprint placements | MEC, rendering, STEP AP242, IDX | Body import bound from the catalog part |
| Envelope | Simplified bodies per part (box, cylinder, extruded profile) | Fast clearance checks, placement | Declared, always conservative |

Planar Booleans, offsets and Minkowski sums with a disc are required from Anvil as operations on planar Bodies, with an integer-coordinate fast path (see Interfaces). Clipper2 implements polygon Booleans and offsetting on 64-bit integer coordinates under the BSL-1.0 licence [47]. Its README describes no arc primitive [47], so Crucible's planar engine adds arcs: it approximates them for the Boolean and reconstructs them in the result, keeping the chord error inside the stated bound.

### One model with the enclosure

**Decision D-ELX-7:** The enclosure and the board live in one design repository and one Kiln graph, so ECAD-MCAD co-design needs no exchange or synchronization step. Shared intent is code: the outline, mounting holes and connector placements may be expressions of enclosure geometry, and the reverse. IDX is used only with tools outside Crucible. *Why:* every exchange step can go stale and must be merged by hand. Fusion places ECAD and MCAD in one environment but still describes cross-domain changes as alerts that prompt review and synchronization [57]. Crucible removes the step itself. A board reused across products is a package whose outline, holes and locked placements are parameters; each product passes values derived from its own enclosure. *Rejected:* an internal IDX-style baseline and increment protocol between ECAD and MCAD documents, which would recreate the sync problem inside one product.

```
let board = pcb(stack, outline: enclosure.face(pcb_shelf).inset(0.5mm))
let mount = enclosure.bosses(m3) |> holes(board, plated: false, d: 3.2mm ± 0.05mm)
place(j1_usb, at: enclosure.cutout(usb).frame.on(board.top), lock: mech)
board.require(clearance(board.assembled(), enclosure.inner_body()) > 0.5mm)
     .require(aligned(j1_usb.body.face(mating), enclosure.cutout(usb), tol: 0.15mm))
```

Behavior in practice:

1. A mechanical engineer moves the USB cutout 2 mm. The connector placement follows on the next build, the ratsnest updates, and DRC flags any track that now violates clearance.
2. A layout engineer cannot drag a placement locked with `lock: mech`; the editor explains the lock and offers to open its source expression.
3. When a placement depends on geometry that no longer exists, the build fails with the typed `ResolveError` from the `Query`. The last valid placement is never kept silently.
4. Height limits come from the enclosure as keep-in volumes. Placement and DRC check the 3D bodies of catalog parts against them, not just a single height number.

### IDX V6 for external tools

The prostep ivip implementor forum completed and released the IDX V6 schema in December 2025 [14]. Splines, 3D keep-outs and chamfered board edges were deferred to V7, and the forum made cloud support a 2026 priority [14].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| IDX export (baseline) | Board outline, holes, cutouts, keepouts, keep-ins, placements and part bodies for one board version | Constructs that V6 cannot represent (splines, 3D keepouts) are approximated by arcs or prisms, with a report and error bounds | Schema validation; re-import comparison | 4 |
| IDX import of change proposals | Each external change becomes an edit on a branch; the set becomes a Proposal with the IDX message attached | Proposals that conflict with locked items are rejected item by item, with reasons sent back as IDX responses | Scripted exchange scenarios recorded from implementor-forum test files [unverified availability] | 4 |
| IDX baseline import | External board becomes a read-only Part with placements | Unmapped items listed | Round-trip on exported baselines | 4 |

IDX runs as an `io/` Wasm component, so it behaves identically on every platform, including the browser.

## PCB layout

### Placement

Interactive placement edits Instance `Transform`s in the `Layout` module. The editor provides drag with live DRC, push of neighbouring parts, align and distribute, flip to the other side, arrays, rooms bound to sub-circuits, and replication of one channel's placement and routing onto its siblings. Replication works because repeated channels are explicit sub-circuit occurrences, so each item maps one-to-one by provenance.

Circuit edits reach the board on the next build, with no annotation step. A new Instance appears in an unplaced tray beside the outline. A removed Instance takes its pads with it; orphaned tracks become DRC errors and are never deleted silently. A changed footprint keeps its placement and reports pads that no longer meet their tracks.

Automatic placement draws on VLSI analytical placement. Cypress (ISPD 2025) places noncritical surface-mount parts by gradient descent on wirelength, electrostatic density and a smooth net-crossing penalty. It handles orientation with a Gumbel-Softmax relaxation and legalizes per board side [5].

Cypress reports 1–5.9× higher routability and up to 492.3× runtime speedup over prior tools, and 54.2% less wirelength on average than human layouts, which the authors note were taken from a larger board and so are not a strict comparison [5]. Its code is Apache-2.0 [6].

The authors list what it lacks: height and alignment constraints, thermal, mechanical and electromagnetic factors, and critical high-current or high-speed parts [5].

**Decision D-ELX-8:** Automatic placement and routing are edit tools, never build steps. Each run writes ordinary edits to the `Layout` module on a branch and opens a Proposal. *Why:* builds stay fast and deterministic; results are reviewable diffs that agents can iterate on; a GPU optimizer's cross-platform rounding never reaches a build. *Rejected:* placement or routing as Kiln-evaluated features, which would rewrite copper after every upstream edit and make builds depend on heuristic search.

Crucible's placer is a Wasm component that orchestrates the optimization. Its heavy kernels, the FFT-based electrostatic density solve and the batched wirelength and crossing gradients, call Flux operations through the host, which provide the wgpu and CPU paths. It adopts Cypress's formulation and extends it with what Cypress lacks:

| Term | Source in the model | Purpose |
| --- | --- | --- |
| Wirelength (log-sum-exp, orientation-aware) | `Circuit` nets | Routability |
| Density (electrostatic, per side) | Footprint courtyards | Overlap removal |
| Net crossing (smooth bell penalty) | Pin pairs per net | Routability [5] |
| Height and keep-in | Enclosure keep-in volumes from MEC | Mechanical fit |
| Thermal spreading | Part power Fields; interactive Flux estimate | Hot-spot avoidance |
| Decoupling loop | Datasheet rules: capacitor-to-pin loop length | Power integrity |
| Critical-net proximity | Net classes with delay or impedance rules | Signal integrity |
| Fixed and partial constraints | `lock`, rooms, alignment groups | Designer intent |

Reductions run in a fixed order, so a run with the same seed and inputs reproduces exactly within a platform class. Benchmarks: the open Cypress suite and its routability metric [5], plus routed results on PCBWorld-Bench boards [30]. Target: match Cypress's published wirelength and routability on its open suite, and finish a single run (without design-space exploration) under 60 s for 500 parts on the reference laptop.

### Design rules and the constraint manager

Design rules are Checks built by constructors in `std::elx::rules`. They live in the design source, so they diff, merge and appear in review like any other code. The constraint manager is a spreadsheet view of those declarations, and editing a cell rewrites the corresponding Ingot expression.

```
let hs = net_class("ddr4_dq", nets: ddr.byte(0).dq + [ddr.byte(0).dm])
rules {
    clearance(all, all) >= fab.min_space                       // from the fabricator record
    width(hs, layer: outer) == impedance_width(40ohm ± 10%)    // solved per layer from the stackup
    delay_match(hs, to: ddr.byte(0).dqs, within: 5ps)
    max_vias(hs) <= 2
    clearance(class("hv_400v"), all) >= creepage(400V, pollution: 2, group: IIIa)
}
```

**Decision D-ELX-9:** Rule precedence is decided by scope specificity, and an ambiguous overlap is a build error that asks for an explicit `override`. *Why:* explicit over magic. A designer can see which rule applies to any object, and an agent cannot change behavior by reordering rules. *Rejected:* numeric priorities. Altium orders basic rules automatically from "All" up to individual objects, but advanced query rules take manually set priorities [54], and those numbers hide intent. Also rejected: a rule store separate from the design (Altium keeps one in `Constraints.xml` and moves changes between schematic and PCB through engineering change orders [54]), because it is a second source of truth.

Specificity order, from least to most specific: board default, layer, net class, net class pair, net, net pair, object. Rules whose scopes are queries rank by the most specific class they name. The constraint manager shows, for any selected object, the rule that won and the rules it shadowed.

| Rule family | Rules |
| --- | --- |
| Clearance | Copper, edge, hole; creepage and clearance by voltage |
| Physical | Width per layer, allowed via types, neck-down |
| Electrical | Impedance, delay, matching, maximum stub, maximum via count, topology |
| Placement | Rooms, height, side, orientation |
| Manufacturing | Annular ring, drill-to-copper, aspect ratio, mask sliver, silkscreen on pad, acid traps |

Manufacturing limits default to the selected fabricator's capability record from MFG, so changing fabricator re-checks the board against its new limits.

### DRC

DRC is a set of checks over the derived copper and hole geometry. Its engine is a Flux-independent Wasm component that uses integer predicates, so every platform reaches the same verdict.

- **Incremental by tile.** The board is split into tiles. Kiln caches each tile's result and re-checks only tiles an edit touched, plus their neighbours within the largest clearance.
- **Indexing.** An R-tree over shapes per layer. Clearance tests compute exact segment, arc and polygon distances in integer arithmetic; arcs use exact squared-distance comparisons.
- **3D checks.** Body-to-body and body-to-enclosure clearance use the catalog parts' envelope Bodies, refined by exact Bodies only where envelopes collide.
- **Reporting.** Each violation names the rule that applied, the shadowed rules and the two objects, and suggests a fix such as "move 0.04 mm" or "neck down to 0.1 mm".

Targets: full DRC of a 20-layer, 10,000-net board under 10 s on the reference laptop; incremental DRC after a routing edit under 50 ms.

Oracle: a protected corpus of boards with seeded violations at random positions and sizes, generated from clean boards, with expected violation sets computed by an independent slow reference checker using exact rational arithmetic. Every seeded violation must be found and no clean region may be flagged.

### Interactive routing

The interactive router supports walkaround, push-and-shove, highlight-collisions and free-angle modes. KiCad's router, a mature open implementation, structures push-and-shove as an iterative shove loop over obstacle lines and vias, with walk-forward and walk-back fallbacks, spring-back nodes for undoing shoves, and post-shove optimization [45]. Crucible keeps that structure and changes three things:

1. **Exact geometry.** All decisions use integer coordinates and exact predicates, so a shove that passes clearance in the router passes DRC.
2. **Rule-aware cost.** Shove and walkaround cost reads the rule set directly, including delay budgets: a shove that would push a matched net out of its delay window is refused, with the reason shown at the cursor.
3. **Recorded sessions.** Each routing gesture is recorded with its inputs, so oracle tests replay real sessions and compare results byte for byte.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Single-track routing | Walkaround, shove or highlight; 45°, 90°, free angle; arcs | Cannot complete: head stops at the last legal point and shows the blocking object | Replay of recorded sessions; DRC clean after every commit | 3 |
| Differential pairs | Coupled routing at the rule gap; gap transitions near pads; uncoupled length tracked | Uncoupled length over limit shown live; commit allowed and flagged | Pair geometry tests; DRC | 3 |
| Drag | Drag segments, corners and vias with shove | Same as routing | Replay | 3 |
| Multi-track and bus routing | Route a group in parallel at the rule pitch | Members that cannot follow stop separately | Replay | 4 |
| Fanout | BGA and QFN escape templates respecting via rules | Unescapable pins listed | Escape completeness tests | 4 |
| Via placement | Layer change with allowed spans only; microvia stacking rules | Disallowed span refused with the rule | DRC | 3 |
| Teardrops | Derived on build from rules, never stored | None | Gerber comparison | 3 |

Targets: under 16 ms per mouse-move update with up to 50 shoved items; commit under 50 ms.

### Length and delay tuning

Constraints may be stated in length or in time. KiCad 10 overhauled tuning to accept time-domain constraints and per-layer tuning profiles [1]. Crucible computes delay from physics instead of a fixed velocity per layer:

1. For each layer and width, a 2D cross-section solve (a Flux quasi-static field solve on the stackup cross-section) yields per-unit-length RLGC, characteristic impedance and propagation delay over frequency. Results are cached per cross-section.
2. Stackup tolerances propagate to delay, so the delay of a net is a `Tol<Time>`. Matching checks the worst case, not the nominal value.
3. Via delays come from a via model (a 3D quasi-static solve per via type, cached), and pin-package delays come from the catalog part's IBIS package data or its pin delay table.
4. Tuning patterns (trombone, sawtooth, accordion) are inserted by the router with spacing chosen so that self-coupling stays under a stated limit. A crosstalk-aware delay check verifies the result.

Match groups express interface rules such as "DQ within ±5 ps of DQS in each byte lane" and "address and command fly-by in order". Catalog packages for DDR, PCIe and USB ship these rule sets.

### Autorouting

**Decision D-ELX-10:** The autorouter is a search-based router shipped as a public Wasm component: negotiated-congestion global routing, gridless shape-based detailed routing, and rip-up and reroute. Learned models may supply cost hints through a plug-in interface but never decide legality. *Why:* PCBWorld, the 2026 engine-grounded benchmark on 679 real boards, reports that learning-based routing still lags rule-based routers [30]. A search-based core is deterministic and explainable. *Rejected:* an end-to-end learned router as the core, which is unproven and hard to explain in review; linking Freerouting, which is GPL-3.0 [35] (it stays usable as an external tool over Specctra DSN and SES for comparison).

Pipeline:

1. **Escape routing** for BGAs and fine-pitch parts, by a flow formulation on the escape grid. The via and layer budget comes from the stackup.
2. **Global routing** on a tile graph with layer assignment, by negotiated congestion (the PathFinder scheme, McMurchie and Ebeling, 1995 [unverified]). Costs include via count, layer preference, critical-net delay windows and keepouts.
3. **Detailed routing** gridless, by A* on a corner graph of inflated obstacles. It is exact in integer coordinates and handles arcs and 45° geometry.
4. **Rip-up and reroute** of failed connections with history costs, then a push-and-shove cleanup pass using the interactive router's engine.
5. **Post-processing:** via minimization, corner smoothing (arcs where the rules allow), teardrops and final DRC.

The output is a set of `Layout` edits on a branch with a Proposal (D-ELX-8), so a human or agent reviews the routed board like any other change.

Commercial references include Cadence Allegro X AI, which automates placement, metal pouring and critical-net routing in the cloud and claims a 10× or greater reduction in turnaround [40]. Quilter generates many candidate boards with reinforcement learning under physics checks [41]. Both claims are vendor-stated.

Measurement: completion rate, via count, wirelength and DRC violations on PCBWorld-Bench boards with its eight engine-checked metrics [30], and routability on the Cypress suite [5]. Freerouting is the open baseline. Target: beat Freerouting's completion rate and via count on PCBWorld-Bench at equal or lower runtime, with zero DRC violations in committed results.

### Pours, planes and vias

**Decision D-ELX-11:** Zone fills are derived on every build, never stored. *Why:* a stale fill is a known way to ship a board with shorts or missing connections; integer clipping makes fills reproducible and fast enough to compute incrementally by tile. *Rejected:* stored fills that must be refilled by hand before output.

- **Zones** have an outline, a net, a layer set, a priority, clearance, minimum width, thermal relief rules per pad type, island policy (remove, keep, keep if larger than an area) and solid or hatched fill. Overlapping zones of equal priority are a build error.
- **Plane splits** are zones on plane layers. A check flags any net whose return path crosses a split: a signal track over a gap in its reference plane.
- **Vias:** through, blind, buried, laser microvias, stacked and staggered microvias, via-in-pad (filled and capped), back-drilled vias with a stub-length rule, stitching and shielding fences generated from rules, and teardrops. Build-up structures such as 2+N+2 and any-layer HDI are expressed as stackup via spans.
- **HDI rules** come from the fabricator capability record: microvia diameter, aspect ratio, capture pad, maximum stacked levels, and whether stacked microvias must be copper-filled.

### Layout capability catalog

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Stackup | Layers, Materials, `Tol` thicknesses, via spans, regions | `StackupError::UnsupportedSpan` naming the nearest supported span | Fabricator capability replay | 3 |
| Board Bodies | Layout data to laminate, copper and assembled Bodies with error bounds | A failed planar Boolean names the items involved; a partial board is never returned | Rasterizer comparison | 3 |
| Enclosure co-design | Outline, holes and placements as expressions of enclosure geometry | `ResolveError` when referenced geometry disappears; locked items refuse drags | Scripted enclosure-change scenarios on golden product 5 | 3 |
| Interactive placement | Instance `Transform` edits with live DRC | Overlaps shown live; commit allowed and flagged | Replay | 3 |
| Automatic placement | Placer run to a Proposal (D-ELX-8) | Infeasible constraints reported by name; a partial result is labelled as partial | Cypress suite; held-out boards | 4 |
| Constraint manager | Spreadsheet view over rule declarations | Ambiguous overlap is a build error asking for `override` | Precedence property tests | 3 |
| DRC | Checks over derived geometry | Violations with rule, objects and suggested fix | Seeded corpus with exact reference | 3 |
| Delay tuning | Field-solved delay as `Tol<Time>` | An unachievable match reports the shortfall | Analytic cases; measured coupons | 3 |
| Autorouting | Router run to a Proposal | Unrouted connections listed; results are never committed with DRC errors | PCBWorld-Bench; held-out boards | 4 |
| Zones and fills | Derived on every build | Equal-priority overlap is a build error; islands handled per policy and reported | Fill oracle | 3 |
| Vias and HDI | Spans from the stackup and the fabricator record | A disallowed span or stack is refused with the rule | DRC corpus | 3 for through, blind and buried; 4 for microvias and HDI |

### Rigid-flex and 3D bending

Rigid-flex boards use stackup regions (see "Stackup"). A flex region adds bend lines, each with a radius, an angle and a bend order. Folding is a feature that builds the folded assembled-board Body from the flat one.

1. Anvil's bend operation maps each flex region from its flat frame onto a cylindrical surface about its bend line, with the neutral axis taken from the flex stackup. Rigid regions move as rigid bodies.
2. Folded copper geometry is derived through the same map, so 3D clearance checks see the real track positions.
3. Checks from IPC-2223 guidance [unverified section numbers]: minimum bend radius as a multiple of flex thickness (one value for static and a larger one for dynamic flexing), no vias or pads in bend zones, staggered conductors across layers, hatched planes in bend areas, and stiffener coverage under connectors.
4. Folding is a pure geometric map. Copper strain in a bend is computed by Flux (a shell or laminate model of the flex region), returned as a `Field<Body, Strain>`, and compared with the copper fatigue curve for dynamic flexing.

The folded and flat boards are two views of one Part. The flat view feeds fabrication outputs, and the folded view is what the enclosure assembly instantiates. Bend order matters for interference, so the fold feature can animate the sequence, and assembly planning (MFG) can reuse it.

### Panelization

A panel is an Assembly of board Instances on a carrier Part (rails, fiducials, tooling holes, coupons). Panel features place copies in an array or a nest, add mouse-bite or V-score breakaways, and generate test coupons such as impedance and IPC-2221 coupons [unverified coupon designations].

Breakaway placement uses the board's 3D bodies to keep overhanging parts clear of tabs and saw paths. Panel checks cover fabricator panel size, V-score keep-outs, tab stress (a Flux plate solve on the depanelling load when the board is fragile) and fiducial visibility. Gerber, ODB++ and IPC-2581 can express panels as step-and-repeat; the exporter uses step-and-repeat where the format allows and flattens otherwise.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Rigid-flex regions | Per-region stackups and layer sets | Item in no region, or on a layer the region lacks, is a DRC error | Region DRC corpus | 4 |
| Bend and fold | Bend lines with radius and order; folded Body with error bound | Radius below the rule fails the check; self-intersection reported with location | Folded geometry compared with analytic cylinder maps | 4 |
| Flex strain | Flux laminate strain Field per bend | Outside envelope (plastic copper) flagged | Analytic thin-beam bending strain, cross-checked with 3D FEM | 4 |
| Panelization | Panel Assembly with breakaways and coupons | Interference with breakaways reported | Panel golden outputs | 3 |

### Fabrication and assembly outputs

Outputs are features that return files into CAS. They are deterministic: the same inputs give byte-identical files, with timestamps taken from the release record, never the clock.

| Output | Standard and version | Contents | Phase |
| --- | --- | --- | --- |
| Gerber X2 | Gerber Layer Format Specification, revision 2026.05 [15] | Copper, mask, paste, silkscreen, outline, with file and aperture attributes | 3 |
| Gerber X3 assembly layers | Same specification; X3 adds per-part assembly data [16][17] | Reference designator, position, rotation, footprint, part number per part | 3 |
| Gerber job file | Gerber Job Format, revision 2020.08 [15] | Stackup, finish, thickness, materials, file list | 3 |
| Drill | XNC, revision 2021.11 [15]; Gerber drill files with X2 attributes as an option | Plated, non-plated, back-drill and laser layers, one file per span | 3 |
| ODB++ | ODB++ version 8.1 [18] | Full product model for fabrication and assembly | 4 (needs format partnership, see Open questions) |
| IPC-2581 | Revision C (December 2020) [19]; later revisions [unverified] | Stackup, layers, BOM, netlist, assembly, rigid-flex and embedded parts | 3 |
| IPC-D-356 | IPC-D-356 netlist [unverified revision] | Test points and netlist for bare-board electrical test | 3 |
| Pick-and-place | CSV with stated columns; IPC-2581 and X3 carry the same data | Designator, X, Y, rotation, side, part number, per variant | 3 |
| BOM | `repo` BOM views (EBOM, MBOM) filtered by variant | Grouped lines, alternates, dated supplier snapshot | 3 |
| Assembly drawings | PDF with fabrication and assembly notes | Views, tables, notes | 3 |
| STEP AP242 | Via the `io/` STEP AP242 writer | Assembled board with part bodies and copper (optional) | 3 |

Every output passes a reader test: Crucible re-imports Gerber, drill and IPC-2581 outputs with independent readers and compares them with the source geometry. IPC-2581 Revision C supports bidirectional DFx feedback between design and manufacturing [19]. Crucible imports fabricator feedback in that form as review comments attached to the objects it names.

Oracle: on golden boards, output-to-source comparison by an independent rasterizer at 1 µm resolution with zero XOR area beyond arc tolerance; ODB++ and IPC-2581 outputs checked with third-party viewers in the release CI.

## Electrical analysis

Every analysis is an Ingot feature that builds a Flux problem or calls a solver Wasm component. It returns Fields and plain values, attaches a `ValidityEnvelope`, and has interactive and sign-off fidelity modes as the contract requires. Results are Kiln-cached by the hash of their inputs, so changing a part value re-runs only the analyses that depend on it.

[[DIAGRAM: Electrical analysis dataflow. Boxes: Circuit, Layout, Stackup, catalog-part models (SPICE, IBIS, Touchstone, thermal) on the left; derived Bodies (copper layers, laminate) in the middle; analysis features (cross-section RLGC, SI channel, PDN, IR drop, EM, thermal, circuit simulation) to the right; outputs as Fields and Checks feeding CI. Arrows: Layout and Stackup to derived Bodies; Bodies and models into analyses; part power Fields from circuit simulation into thermal; temperature Field back into circuit simulation and IR drop.]]

### Signal integrity

| Capability | Method | Contract | Validity envelope | Phase |
| --- | --- | --- | --- | --- |
| Impedance and RLGC per cross-section | 2D quasi-static field solve on the stackup cross-section (method of moments or FEM in Flux); frequency-dependent conductor loss with surface roughness; causal dielectric model | `(Layer, width, gap) -> Field<FreqSpan, Rlgc>` with tolerance bands | TEM and quasi-TEM, to the frequency where the cross-section is a tenth of a wavelength | 3 |
| Pre-layout topology | What-if channels from symbolic topologies before routing | Topology value -> eye and timing metrics | As channel simulation | 4 |
| Post-layout extraction | Net segmentation into transmission lines, vias (3D quasi-static or full-wave per via type) and discontinuities | `Net -> Field<FreqSpan, SParams>` per net group | Per segment envelope | 4 |
| Crosstalk | Coupled-line extraction of aggressor sets within a coupling window; NEXT and FEXT in time domain | Victim noise waveforms and peak values vs. budget | Weak coupling assumed outside the window; window size reported | 4 |
| S-parameter handling | Touchstone 2.1 [20] I/O; passivity and causality checks; vector-fitting macromodels with passivity enforcement | `Touchstone -> RationalModel` with fit error | Fit error reported per port pair | 4 |
| Channel simulation | Statistical eye (peak distortion and convolution) and time-domain bit-by-bit with IBIS-AMI equalization models | Eye height, width and BER contour vs. mask | Linear time-invariant channel for statistical mode | 4 |
| Driver and receiver models | IBIS 8.0 [21], including its power-aware keywords [unverified]; IBIS-AMI executable models | Behavioral I-V and V-t tables; AMI algorithmic models | IBIS envelope; AMI model's stated rates | 4 |
| Return-path checks | Reference-plane continuity, layer changes without return vias, split crossings | Checks with locations | Geometric | 3 |

**Decision D-ELX-12:** IBIS-AMI executables run only in an out-of-process host, never inside Kiln evaluation or the core process. *Why:* AMI models are vendor-compiled native libraries for specific operating systems and CPUs, and they cannot be sandboxed as Wasm components. Running them in a separate host keeps the core safe and the rest of the analysis deterministic. Their results are cached and labelled with the host platform, and missing platform builds are reported, not emulated. *Rejected:* loading AMI libraries into the core process, which violates the sandbox rule and the platform-parity requirement.

Rational fitting uses vector fitting (Gustavsen and Semlyen, 1999 [52]) in its relaxed and fast variants [unverified citations for the variants]. Residue perturbation enforces passivity, as in the SINTEF Matrix Fitting Toolbox [52], and a Hamiltonian eigenvalue test checks it [unverified citation]. Fit error and enforcement perturbation are reported in the model's `ErrorBound`, and fitting runs in Rust on faer, which is MIT-licensed [48].

The IBIS Open Forum ratified IBIS 8.0 on 5 December 2025 [21]. The current Touchstone version is 2.1 and IBIS-ISS is at 1.0 [20]. Crucible's IBIS parser is validated against the IBIS Open Forum's IBISCHK8 parser output [20].

| SI capability | Failure behavior | Oracle |
| --- | --- | --- |
| Impedance and RLGC | Frequencies beyond the quasi-TEM limit are flagged with the limit; a dielectric without frequency data is an error naming the Material | Conformal-mapping solutions for stripline, microstrip and coplanar lines; measured coupons |
| Pre-layout topology | An unknown topology element is a typed error | Agreement with post-layout results on golden boards |
| Post-layout extraction | A discontinuity without a model falls back to a full-wave solve of that segment, and the cost is reported; it is never ignored | Full-wave references for via and connector test structures |
| Crosstalk | Aggressors outside the coupling window are not computed, and the window is reported | Weak-coupling analytic formulas; measured coupons |
| S-parameter handling | Non-passive or non-causal data is flagged at the offending frequencies; a failed fit reports its worst error | Hamiltonian re-check; measured Touchstone corpus |
| Channel simulation | A non-linear or time-varying channel in statistical mode is refused with the reason; a missing AMI platform build is reported | Vendor AMI examples; IEEE 802.3 reference channels [unverified] |
| Driver and receiver models | IBIS parse errors are reported with line numbers | IBISCHK8 output comparison [20] |
| Return-path checks | Violations reported with locations | Seeded geometric corpus |

### Power integrity

| Capability | Method | Contract | Validity envelope | Phase |
| --- | --- | --- | --- | --- |
| Target impedance | Ztarget = allowed ripple ÷ transient current, per rail and band, from catalog-part load data or circuit simulation | `Rail -> Field<FreqSpan, Impedance>` mask | Linear PDN assumption | 3 |
| PDN impedance | 2.5D plane-pair solve (Flux): the Helmholtz equation for parallel-plate modes on each plane pair, coupled through via models, with capacitor models (C, ESR, ESL or vendor Touchstone) and a VRM model | `Board, Rail -> Field<FreqSpan, Impedance>` at each load port | Plane spacing much smaller than wavelength; sign-off above that limit uses full-wave Flux | 4 |
| Decoupling optimization | Choose capacitor types, counts and sites to meet the mask at least cost. Greedy insertion and local search on rational-fit models; exact mixed-integer solution for small instances as a check | Edit Proposal with placements, plus the before and after Z(f) | As PDN impedance | 4 |
| IR drop and current density | DC conduction on copper sheets (Flux thin-sheet model per layer), joined through via and plating resistances; copper resistivity follows the temperature Field | Voltage-drop and current-density `Field<Body, …>` per layer; per-via current; checks against limits | DC; copper below its recrystallization range | 3 |
| Plane resonance | Eigenmodes of plane pairs; flags resonances inside rail noise bands | Mode list with Fields | As PDN impedance | 4 |
| Electro-thermal coupling | Fixed-point loop: IR drop gives Joule heat, Flux thermal gives temperature, temperature updates resistivity; Aitken relaxation | Converged Fields and the final residual | Converges when the heating is mild; non-convergence is reported with the residual history | 4 |

| PI capability | Failure behavior | Oracle |
| --- | --- | --- |
| Target impedance | Missing load data leaves the check unverified, never passed | Hand-computed masks |
| PDN impedance | Frequencies above the plane-pair limit are flagged, and full-wave sign-off is suggested | Analytic parallel-plate cavity resonances; VNA measurement on golden product 5 |
| Decoupling optimization | An infeasible mask reports the lowest achievable impedance and the band where it fails | Exact mixed-integer optimum on small instances |
| IR drop and current density | Limits exceeded fail the check with location, value and limit | Analytic strip and annulus resistances; four-wire measurement |
| Plane resonance | Resonances inside noise bands are listed as warnings | Analytic cavity modes |
| Electro-thermal coupling | Non-convergence is reported with the residual history | Analytic self-heating of a uniform strip |

### EMC and EMI

ELX builds the excitations and geometry, and Flux solves the fields. Results are screening estimates with stated uncertainty, never compliance verdicts.

- **Radiated emissions screening.** Common-mode and differential-mode currents from circuit simulation and SI become current-density Fields on the copper Bodies. Flux full-wave computes far-field strength at 3 m or 10 m and compares it with the chosen limit lines. The enclosure, cables and harness can be included because they are in the same model.
- **Conducted emissions.** A line impedance stabilization network model sits in the circuit simulation. Layout parasitics for hot loops come from Flux quasi-static extraction. Filter design uses the same matching and optimization tools as RF.
- **Immunity and ESD screening.** Port-level transient injections in circuit simulation, with the layout's extracted coupling. The output is a ranked list of vulnerable nets.
- **Design-rule screening.** Fast geometric checks run on every build: return-path discontinuities, slots under clock nets, unstitched plane edges, long stubs and missing ground vias at layer changes.

### Thermal

Part power becomes a Field and enters Flux heat transfer.

1. **Power sources.** Each catalog part's dissipation comes from circuit simulation (time-averaged over a stated window), from a declared operating mode, or from datasheet typical values. The source is labelled, so reviewers can see which parts use estimates.
2. **Package models.** Two-resistor and DELPHI compact models from the catalog part, per JEDEC JESD15 [unverified part numbers], or the full package Body when the vendor provides one.
3. **Board model.** Interactive mode uses an orthotropic effective conductivity per layer and tile, computed from copper coverage. Sign-off mode meshes explicit copper, using the derived copper solids or an immersed method on them.
4. **Environment.** Natural or forced convection, radiation, heat sinks and the enclosure come from Flux conjugate heat transfer, using the enclosure Body directly.
5. **Outputs.** A temperature `Field<Body, Temperature>`, junction temperatures per part, and checks against catalog limits and derating rules. Temperatures feed back into circuit simulation, IR drop and reliability.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Radiated emissions screening | Current-density Fields on copper and cables to far-field strength versus limit lines, with an uncertainty band | Results are labelled as screening; a missing cable or enclosure model is listed as an assumption | Analytic small-loop and short-dipole radiation; chamber scans of golden product 6 | 4 |
| Conducted emissions | Circuit simulation with a LISN model and extracted parasitics | Unmodelled parasitics are listed | Pre-compliance measurements of golden product 5 | 4 |
| Immunity and ESD screening | Ranked vulnerable nets | Screening label | Seeded coupling cases | 5 |
| EMC rule screening | Geometric checks on every build | Violations with locations | Seeded corpus | 3 |
| Board thermal | Part power Fields to temperature Fields and junction temperatures | Missing power data is labelled as an estimate; a part without a thermal model uses its θJA with a warning | Analytic fin and plate cases; thermocouple data from golden product 5 | 3 |

## Circuit simulation

### Engine choice

| Engine | Licence | Strength | Fit for Crucible |
| --- | --- | --- | --- |
| ngspice | BSD-3-Clause core; LGPL-2 numparam, KLU and tclspice; a few GPL-2+ XSPICE table-model files [8] | Broadest SPICE compatibility; mixed-signal with event-driven digital [7] | Reference and compatibility engine, out of process |
| VACASK | AGPL-3.0 [9] | Fast: 57.98 s on the C6288 benchmark against ngspice's 71.81 s and Xyce's 151.57 s, authors' figures; HB, PSS and noise analyses [9] | External cross-check only (AGPL) |
| Xyce | GPL-3.0 [60] | MPI parallel; harmonic balance [60] | External cross-check only (GPL) |
| OpenVAF | GPL-3.0 [10] | Compiles Verilog-A to OSDI shared objects [10] | Not linked; Crucible compiles Verilog-A itself |
| Crucible engine | Apache-2.0 or MIT, Rust | Native Fields, AD, Wasm, GPU batching | Primary engine |

**Decision D-ELX-13:** Crucible's circuit simulator is written in Rust as Flux operations. It uses modified nodal analysis, Newton iteration with homotopy fallbacks, BDF of orders 1 and 2 and trapezoidal integration with local-truncation-error control, and sparse LU with block triangular form, a fill-reducing ordering per block and fast numeric refactorization when only values change. That is the scheme of KLU (Davis and Palamadai Natarajan, ACM TOMS, 2010 [unverified citation]); KLU itself ships inside ngspice under LGPL-2 [8], so Crucible implements the scheme on faer's MIT-licensed sparse LU, AMD and COLAMD orderings [48]. ngspice runs out of process as a compatibility reference and an oracle. *Why:* the engine must run in the browser and in Wasm, return Fields, couple to temperature Fields, give adjoint sensitivities through Flux's form-level AD, and batch thousands of Monte Carlo samples on the GPU. No existing permissively licensed engine combines these. *Rejected:* linking ngspice, whose LGPL and GPL-2+ files [8] would need careful exclusion and which still lacks AD and Wasm parity; VACASK and Xyce, which are AGPL and GPL [9][60]; OpenVAF, which is GPL-3.0 and emits native shared objects that cannot run in a browser [10].

**Decision D-ELX-14:** Crucible's Verilog-A front end, itself a public Wasm component, lowers compact models to Flux's kernel IR. Flux then generates CPU, GPU and Wasm kernels with AD Jacobians from that IR, and the cache key covers the Verilog-A source, the front-end version and the target. *Why:* compact models (BSIM, PSP, VBIC and vendor models) are distributed as Verilog-A. One IR gives native speed on desktops, GPU batches for Monte Carlo and Wasm in the browser, with no third-party native code. *Rejected:* OSDI shared objects, which are native and platform-specific; Wasm-only device models, which cannot run in GPU batches.

SPICE3 device models (diode, BJT Gummel-Poon, JFET, MOSFET levels 1–3, VDMOS, transmission lines) are ported to Rust from ngspice's BSD-3-Clause device code [8], keeping its attribution. Each ported model must match ngspice on a regression corpus before it is enabled.

A design may select `engine: ngspice` for one analysis explicitly. The run then executes out of process and is labelled as such (CCR-2). This keeps rare dialect features usable while the native engine catches up; it is never chosen silently.

### Netlist and model import

The importer reads SPICE netlists and libraries in the ngspice, PSpice and LTspice dialects as a Wasm component. Unsupported constructs, such as an encrypted PSpice model, are listed with their file and line and never skipped silently. Imported subcircuits become catalog-part simulation models with their source text stored, so a review can see what was imported.

### Analyses

| Analysis | Method | Contract | Failure behavior | Phase |
| --- | --- | --- | --- | --- |
| Operating point | Newton with damping; gmin stepping, source stepping and pseudo-transient homotopy, tried in that order | Node voltages and branch currents; device operating regions | Non-convergence returns the nodes with the largest residuals and suggests a fix, such as a missing DC path to ground | 3 |
| DC sweep | Continuation from the previous point | `Field<Sweep, V>` | As above, per point | 3 |
| AC small-signal | Linearize at the operating point; complex sparse LU per frequency | `Field<FreqSpan, Complex<V>>` | Singular matrix names the floating node set | 3 |
| Noise | Adjoint noise per source | Spectral densities per source and total | As AC | 3 |
| Transient | BDF orders 1–2 and trapezoidal with LTE control; breakpoints at source edges and switch events; a switch from trapezoidal to BDF2 when trapezoidal ringing is detected | `Field<TimeSpan, V>` | Step-size collapse reports the time, the device and the nodes involved | 3 |
| Sensitivity | Adjoint DC, AC and transient sensitivities from Flux AD | Gradients of any measured output with respect to parameters | None beyond the analysis' own | 4 |
| Monte Carlo and corners | Samples from `Tol` distributions and correlated part lots; GPU-batched device evaluation | Yield and output distributions | Failed samples are counted and reported, never dropped | 3 |
| Worst case | Corner search guided by sensitivities, then confirmed by simulation | Worst-case value and parameter set | None beyond the analysis' own | 4 |
| Pole-zero and loop stability | Poles and zeros from the generalized eigenvalue problem of the linearized system; loop gain by the Middlebrook or Tian method [unverified citations]; phase and gain margins | Poles, zeros, margins and Bode Fields | As AC | 3 |
| Periodic steady state | Shooting Newton; harmonic balance for RF and mixers | Spectra and periodic waveforms | Divergence reported with the iteration history | 5 |

Monte Carlo is deterministic: samples come from a counter-based random generator keyed by (design hash, analysis id, sample index). The same seed gives the same samples on every platform, and adding samples never changes earlier ones.

All analyses use fixed reduction orders and no data-dependent threading, so results are bit-identical within a platform class (which includes the GPU backend) and agree across classes within each analysis's declared tolerance.

Targets:

- C6288 benchmark with PSP103.4 models: within 1.2× of VACASK's runtime on the same machine (target).
- Regression corpus: results within relative 10⁻³ or absolute 1 µV of ngspice, whichever is larger (target).
- Monte Carlo: 10,000 samples of a 200-node analog circuit's AC response in under 60 s on the reference laptop GPU (target).

### Mixed-signal

The engine includes an event-driven digital kernel with four-state logic, delays, and gates, flip-flops, counters and lookup tables, in the style of XSPICE. Analog-to-digital bridges have thresholds and hysteresis, digital-to-analog bridges have drive strength and edge rates, and digital events become analog breakpoints. Larger digital blocks connect in two ways:

- **HDL co-simulation.** Verilog and SystemVerilog are compiled with Verilator, an external tool licensed LGPL-3.0 or Artistic-2.0 [29], and run as a co-simulation participant. The generated model is never linked into the core.
- **Firmware.** Microcontrollers run real firmware in Renode (see "Firmware-in-the-loop"), with GPIO, ADC, PWM, timers and serial buses connected to circuit nets.

### Lumped networks beyond electronics

**Decision D-ELX-15:** `Circuit` is the network type for every lumped physical domain. Ports are typed by domain: electrical, magnetic, thermal, rotational, translational, fluid or signal. The same `connect` statement and the same DAE pipeline serve circuits, motor drives, drivetrains and battery packs. *Why:* one connection mechanism replaces the usual split between a circuit simulator, a block-diagram tool and a physical-network tool. A motor drive is then one model: inverter, motor, shaft, gearbox and load. *Rejected:* separate formalisms per domain, which need adapters at every boundary.

The compiler checks domain compatibility at each `connect`. Across variables (voltage, temperature, angle) are equal at a node; through variables (current, heat flow, torque) sum to zero. Signal ports are causal and directional.

The network compiler is a Flux operation, because mechanical drivetrains, batteries and controls depend on it as much as circuits do. Its pipeline: flatten the network, apply structural analysis (Pantelides index reduction, block lower-triangular ordering, tearing), generate residual and Jacobian code, then integrate with Flux's DAE solver. Electrical subsystems keep the MNA-specialised fast path.

The validity envelope of a lumped network is stated per element; lumped wiring, for example, is valid while the line is shorter than a tenth of a wavelength. Elements used outside their envelope are flagged.

### Reliability prediction and derating

Reliability prediction gives failure rates for comparison and allocation, not a forecast of field life. Every result names the handbook it used, because handbooks disagree by large factors.

| Method | Edition | Approach | Crucible use |
| --- | --- | --- | --- |
| FIDES | Guide 2022 Edition A [59] | Physics-of-failure informed, based on test data, field returns and existing models [59]; base rates adjusted by Π factors for process, application and ruggedization (described for the 2004 and 2009 editions [58]) | Default for new designs; guides require registration [59] |
| Telcordia SR-332 | Issue 4, March 2016 [58] | Bell Labs-modified MIL-HDBK-217 approach; burn-in, lab and field data; confidence bounds per part [58] | Telecom customers |
| MIL-HDBK-217F | Notice 2 [58] | Parts count and parts stress [58] | Legacy and defence contracts |
| IEC 61709, via SN 29500 | SN 29500 is based on IEC 61709 [58] | Reference-condition failure rates converted to operating conditions [58] | Industrial customers |
| Physics of failure | Models in Flux | Solder-joint fatigue (Engelmaier-type strain-range models; Coffin-Manson with Flux thermomechanical strain), electromigration (Black's equation), electrolytic capacitor wear-out (Arrhenius) | Sign-off for critical joints and parts |

Handbook tables are copyrighted. Crucible ships the calculation engines and accepts the tables as licensed data packages. Where a table is not free to redistribute, the package contains only the user's licensed copy, which stays outside the public registry.

- **Mission profiles.** A mission profile is an Ingot value: phases with ambient temperature, power state, humidity, vibration and duty cycle. Part stresses come from circuit simulation and thermal results per phase, not from hand-entered numbers.
- **Derating.** Derating rules are checks per part category. The defaults follow the ECSS-Q-ST-30-11C [unverified edition] and NAVSEA SD-18 [unverified] rule sets, encoded as licensed data where required. Each rule names its source, and a violation shows the actual stress, the allowed stress and the margin.
- **System reliability.** Reliability block diagrams and fault trees are built from the `Circuit` hierarchy and the system architecture. They feed FMEA tables in the system model (see "System modeling and traceability").

Oracle: the handbook worked examples, computed by the engine and compared with the published values to the printed precision; physics-of-failure models compared with the published experimental datasets they cite.

### DFM, DFA and test for assembled boards

Manufacturing (MFG) owns process capability records, assembly process planning and factory data. `std::elx` turns those records into checks on the board.

| Check family | Examples | Data source |
| --- | --- | --- |
| Fabrication | Annular ring, drill-to-copper, aspect ratio, mask sliver and web, copper balance per layer, acid traps, starved thermals, minimum feature by copper weight | Fabricator capability record (MFG) |
| Assembly | Courtyard overlap, part-to-part spacing by package pair, wave-solder shadowing and orientation, polarity mark visibility, fiducials (global and local for fine pitch), tombstoning risk from pad thermal asymmetry, paste-to-pad ratio, via-in-pad without fill | Assembly line capability record (MFG) |
| Thermal profile | Peak and time-above-liquidus per part versus its moisture sensitivity level and maximum reflow temperature, from a Flux transient thermal solve of the reflow profile | Reflow profile record (MFG); catalog part limits |
| Test | Test-point coverage per net, probe spacing, fixture side, boundary-scan chain integrity | Test strategy record (MFG) |
| Rework and inspection | BGA rework clearance, X-ray inspection need for hidden joints, conformal-coat keepouts | Process record (MFG) |

The fabricator's DFx feedback, imported through IPC-2581 Revision C [19], appears as comments on the board objects it names. Repeated feedback for one rule becomes a candidate rule change, which is opened as a Proposal.

## Mechatronics

### Electric machines

Crucible models machines at three fidelities. Each fidelity is a `Circuit` element with rotational and electrical ports, so a drive simulation can switch fidelity without rewiring.

| Fidelity | Model | Source of parameters | Use |
| --- | --- | --- | --- |
| Lumped | dq model with saturation lookup tables (flux linkage as a function of id, iq and rotor angle), iron-loss resistance, thermal network | Catalog part data, or extracted from a Flux solve | System and controls simulation |
| Reduced-order map | Flux-linkage and torque maps over (id, iq, θ), plus loss maps | Batch of Flux magnetostatic solves on the machine Body | Drive design, efficiency maps, controller tuning |
| Field | Transient 2D or 3D magnetodynamics with motion, eddy currents in magnets and laminations, coupled to the drive circuit | Flux electromagnetics on the machine Body | Sign-off: torque ripple, cogging, losses, demagnetization |

Machine design features build motor geometry from typed parameters: stator and rotor laminations, slots, windings and magnets, for surface-PM, interior-PM, induction, synchronous reluctance, switched reluctance, axial-flux and linear machines. Winding layout uses the star-of-slots method with winding-factor computation. Outputs: torque-speed envelope, efficiency map, back-EMF, cogging, torque ripple, short-circuit and demagnetization margins, and loss Fields (copper with AC effects, iron by a selectable loss model, magnet eddy losses) that feed Flux thermal analysis.

Pyleecan is Apache-2.0 and covers similar 2D radial-flux topologies, but it couples to FEMM, which it supports only on Windows [44]. That limitation is why Crucible solves machine magnetics in Flux rather than wrapping an external solver.

**Decision D-ELX-16:** Efficiency and loss maps are computed from Flux magnetostatic solves with motion handled by the Flux sliding-interface or mortar method, and current-dependent saturation is captured per (id, iq) point. Solves for different operating points run in parallel and are cached individually. *Why:* map points are independent, so the work parallelizes cleanly and Kiln can reuse every point after an edit that changes only the control strategy. *Rejected:* analytic machine models only, which do not capture saturation or slot effects; a single transient solve per operating point, which costs far more than a map needs.

Actuators use the same machinery: solenoids and voice-coil actuators through magnetostatic force maps, piezo stacks through a coupled piezoelectric model in Flux with a lumped equivalent (a Butterworth-Van Dyke style network) for circuit use.

### Sensors

Sensors are catalog parts or designed parts with three model layers:

1. **Physical transduction.** Optional Flux model of the sensing physics, such as a Hall element in a magnet's field, a strain gauge on a Flux strain Field, or a capacitive electrode in an electrostatic solve.
2. **Behavioral model.** Transfer function, noise density, bandwidth, nonlinearity, cross-axis sensitivity, temperature drift and quantization, as an element with physical input ports and electrical or digital output ports.
3. **Interface model.** The digital bus behavior (I2C or SPI registers) for firmware-in-the-loop, generated from a register description such as CMSIS-SVD or SystemRDL [unverified that both are supported by Renode peripheral generation].

A sensor's error budget is a check over the three layers: for example, encoder angle error under 0.1° including magnet tolerance, air-gap variation and temperature.

### Drives and gear trains

Inverter and drive models range from averaged switch models (for control design) to switching models with device losses (for thermal design). Device losses come from catalog-part switching-energy curves or from device simulation. The motor, inverter and DC link connect through `Circuit` ports (D-ELX-15).

Gear trains, couplings, belts and bearings come from Mechanical (MEC) as lumped elements with rotational ports: ratio, efficiency, inertia, backlash and stiffness. A gearbox designed in MEC exports its lumped model automatically from its geometry and material, so golden product 3 (the gearbox) and a motor from `std::elx` form one drivetrain model.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Machine geometry features | Typed parameters to machine Bodies and winding layout | Infeasible geometry (slot overlap, negative tooth width) is a typed error | Winding-factor tables for standard windings | 4 |
| Lumped machine model | dq model with saturation tables as a `Circuit` element | Operation outside the table range is flagged, never extrapolated silently | Analytic linear-machine cases | 4 |
| Flux-linkage, torque and loss maps | Batch magnetostatic solves to maps with interpolation error | Points that fail to converge are reported, and the map marks them | Analytic slotless machine fields; TEAM problems [unverified] | 4 |
| Transient machine sign-off | Magnetodynamics with motion, coupled to the drive circuit | Divergence reported with time and region | Cogging and back-EMF measurements on golden product 6 motors | 4 |
| Actuators | Force maps and lumped models | As machine maps | Analytic solenoid force | 4 |
| Sensor models | Three-layer models with error budgets as checks | A missing layer leaves the budget unverified | Datasheet transfer curves; bench data | 4 |
| Drive models | Averaged and switching inverter models with losses | Missing switching curves are listed | Analytic averaged-model cases; ngspice reference | 4 |
| Drivetrain coupling | MEC lumped gear elements joined to `std::elx` machines | Port domain mismatch is a compile error | Golden product 3 gearbox driven by a lumped motor | 2 |

## Controls

### Representations

Control design uses plain Ingot values, with no separate block-diagram language:

| Representation | Type | Operations |
| --- | --- | --- |
| Transfer function | `Tf<In, Out>` over s or z, coefficients as `Quantity` with units checked across the loop | Series, parallel, feedback, discretize (ZOH, FOH, Tustin with prewarp), minimal realization |
| State space | `Ss<In, Out>` with matrices whose rows and columns are typed signals | Controllability, observability, balanced truncation, Kalman decomposition |
| Zero-pole-gain and frequency response | `Zpk`, and `Field<FreqSpan, Complex<…>>` for measured data | Bode, Nyquist, Nichols, margins, sensitivity and complementary sensitivity |
| Block diagram | A `Circuit` whose ports are signal ports | Same editor as schematics, signal-flow layout; flattening to state space |
| Hybrid and discrete-event | State machines with typed events, attached to a `Circuit` | Simulation with event detection |

Unit typing matters here. A controller whose gain multiplies a position error in metres to produce a torque in newton-metres has type `Quantity<Torque / Length>`, so a missing conversion fails at compile time.

### Design methods

| Method | Implementation | Contract | Phase |
| --- | --- | --- | --- |
| PID with anti-windup and filtering | Loop shaping; robust tuning by constrained optimization of a margin objective | Gains plus guaranteed margins on the nominal plant and a stated uncertainty set | 4 |
| Linearization | Exact Jacobians of the plant DAE at an operating point via Flux AD | `Ss` with the operating point recorded | 4 |
| LQR, LQG, Kalman filters | Riccati solvers (Schur method) in Rust on faer | Gains with closed-loop pole report | 4 |
| H∞ and µ-synthesis | Structured H∞ via nonsmooth optimization; LMI formulations through a conic solver | Controller plus achieved norm | 5 |
| Model predictive control | Code-generated condensed or sparse QP; solved by Clarabel (Apache-2.0, interior point with a homogeneous embedding [49]) or by an ADMM solver for embedded targets | Controller code and closed-loop simulation | 5 |
| System identification | Prediction-error methods and subspace identification (N4SID) from measured or simulated data | Model with fit and residual tests | 4 |
| Model order reduction | Balanced truncation with error bound; Krylov reduction for large FEM-derived plants | Reduced `Ss` plus the a-priori H∞ error bound | 4 |

Plants come from three sources: multibody models (MEC) linearized at an operating point, electrical and electromechanical networks (D-ELX-15), and Flux field models reduced by model order reduction. A structural mode from a Flux modal analysis becomes a plant pole pair with its damping, so a control loop can be checked against frame resonances, as the drone of golden product 6 requires.

**Code generation.** A controller exports as fixed-point or floating-point C with a stated numeric format and a test harness that compares it bit-for-bit against the Ingot reference on recorded inputs. The generated code is a software item in the BOM (see "System modeling and traceability").

| Capability | Failure behavior | Oracle |
| --- | --- | --- |
| Transfer function and state-space algebra | Unit mismatch around a loop is a compile error; non-minimal realizations are reported | Closed-form textbook cases |
| Linearization | A non-smooth operating point (contact or saturation) is flagged | Finite-difference cross-check |
| LQR, LQG and Kalman | No stabilizing solution: the uncontrollable or undetectable modes are reported | Closed-form scalar and double-integrator cases |
| H∞ synthesis | Infeasible bound: the best achieved norm is reported | Published benchmark plants [unverified] |
| MPC | Infeasible QP at runtime is reported with the active constraints | Maros-Meszaros QP set [unverified] for the solver; closed-loop reference runs |
| System identification | Poor fit is reported with residual whiteness tests | Synthetic data from known systems |
| Model order reduction | The a-priori error bound is reported with the reduced model | Bound never exceeded on test plants |
| Code generation | Fixed-point overflow found in tests is reported with the signal and input | Bit-exact comparison with the Ingot reference |

### Co-simulation over FMI and SSP

Interop standards are fixed by the contract: FMI 3.0.2 and SSP 2.0.1. FMI 3.0.2 is a maintenance release with no new features over 3.0.1, and FMUs remain valid across 3.0, 3.0.1 and 3.0.2 [12]. SSP 2.0 supports FMI 3.0 models and virtual ECUs [13].

The SSP project's site lists a 2.0.1 release and a Traceability layered standard at version 1.0.0 [11]. FMI-LS-BUS 1.0, released on 21 July 2025, covers CAN, CAN FD and CAN XL [26][27]. A 1.1 beta adds FlexRay and Ethernet [26], a 1.3 alpha published in January 2026 adds LIN, and a 1.3 beta followed in June 2026 [27].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| FMU import (CS, ME, SE) | An FMU becomes a `Circuit` element with typed ports from its modelDescription; units mapped to `Quantity` types | Unmappable unit or variability is a typed import error; missing binaries for the current platform are reported with the platforms that are present | Reference FMUs and cross-check FMUs [unverified] | 4 |
| FMU export | Any `Circuit` or control model exports as an FMI 3.0 FMU with source code, plus binaries for Tier 1 platforms | Constructs without FMI equivalents are listed | Import into two external tools in CI | 4 |
| Master algorithms | Fixed step; variable step with step rejection where FMUs support state saving; FMI 3.0 clocks and event mode; intermediate updates | Divergence reported with the participant and time | Analytic coupled-oscillator benchmarks with known coupling error | 4 |
| Strong coupling | ME FMUs integrated in one solver; algebraic loops solved with the FMI 3.0 directional derivatives | Unsolvable loops reported with the variables involved | Benchmarks | 5 |
| SSP | Import and export of system structures, parameter sets and mappings | Unmapped elements listed | SSP example files [unverified] | 4 |
| Bus simulation | FMI-LS-BUS network abstraction for CAN family; LIN and Ethernet as the layered standard matures | Unsupported bus features reported | LS-BUS reference examples [unverified] | 5 |

**Decision D-ELX-17:** FMUs and other native co-simulation participants run in an out-of-process host, and a deterministic master orchestrates them. Results are cached by the hash of the FMU archive, the master settings and the inputs. Every result is labelled with the platform class that produced it. *Why:* FMU binaries are native code from third parties. Isolation protects the core, and labelling keeps the determinism promise honest: two platforms may disagree, and the label shows it. FMUs with source code are compiled to Wasm components where possible, which restores full portability. *Rejected:* in-process loading of FMU binaries.

**Modelica.** Crucible reaches Modelica through FMUs in phase 4. The Modelica Standard Library is BSD-3-Clause, and v4.1.0 was released on 23 May 2025 [61].

OpenModelica can export FMUs as an external tool [unverified]. Its licence, OSMC-PL 1.8, lets non-members of the consortium use it only under AGPL-3.0 [63], so it is never linked.

Native Modelica compilation is a phase 5 option: Rumoca is an Apache-2.0 Modelica compiler in Rust, in active development and described by its authors as having rough edges [50]. It could feed the D-ELX-15 DAE pipeline. ModelingToolkit shows the acausal, symbolic approach with automatic index reduction that the pipeline adopts [51].

### Firmware-in-the-loop

Real firmware binaries run in an emulator connected to the circuit and plant models.

**Decision D-ELX-18:** Renode is the default firmware emulator, and QEMU is the alternative for application processors. Both run out of process, which QEMU's GPL licence [unverified] makes mandatory. Renode is MIT-licensed. It runs unmodified firmware binaries on Arm Cortex-M, Cortex-A and Cortex-R, RISC-V, x86, Xtensa and other cores, models multi-node networks, and ships for Linux, macOS and Windows [28]. *Why:* the license is permissive, coverage of microcontrollers is broad, and peripheral models are scriptable. Renode also co-simulates RTL through Verilator [62], which covers FPGA-based designs. *Rejected:* writing a Crucible emulator, which would duplicate a large, mature effort; vendor-specific simulators, which cover single chip families.

Coupling contract:

1. **Peripheral bridge.** Each microcontroller pin, ADC channel, DAC, timer and PWM output, and serial bus maps to a net or signal port in the `Circuit`. The mapping comes from the catalog part's pin facet and the firmware's board description, and it is checked for consistency at build time.
2. **Time synchronization.** The master advances emulator and circuit in lock-step quanta (default 10 µs, configurable). PWM edges and ADC sample instants cross as timestamped events that become circuit breakpoints; the result reports the timing error the quantum allows.
3. **Determinism.** With a fixed quantum, fixed seeds and deterministic peripheral models, runs are repeatable, and the ELF hash enters the cache key. Renode describes its environment as deterministic [62]; Crucible verifies this per release by repeating runs and comparing traces.
4. **Observability.** Firmware variables (from DWARF debug information) appear as signals beside circuit and plant signals in one timeline. GDB attaches through the emulator for debugging.
5. **Tests.** Firmware tests are checks: for example, `require(settle_time(motor.speed, to: 3000rpm, within: 2%) < 150ms)`. They run in CI against the emulated board.

### Hardware-in-the-loop

Hardware-in-the-loop (HIL) needs real-time execution, which the deterministic Kiln evaluator cannot provide. Crucible provides hooks and evidence, not a real-time runtime:

- **Export.** Plant models export as FMUs, or as generated C with a fixed-step solver, for third-party real-time targets.
- **Bench adapters.** A bench adapter maps model signals to instrument channels: data acquisition, CAN interfaces and power supplies via SCPI. Adapters are external programs that talk to `api`.
- **Evidence.** HIL runs record their inputs and outputs and attach them to a Proposal or release as test evidence. Checks can compare recorded results with simulation within stated tolerances.
- **Labelling.** A HIL result is never cached as an evaluation result. It is a dated measurement with provenance, like physical test data.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Firmware-in-the-loop | ELF plus board description to co-simulated traces and checks | Pin-map mismatch is a build error; an unsupported peripheral model is listed and the run refused | Reference firmware with recorded traces; repeated-run identity | 4 |
| Lock-step coupling | Quantum-based synchronization with event timestamps | The timing error bound is reported with every result | Analytic PWM-to-RC filter cases | 4 |
| RTL co-simulation | Verilator models attached through Renode [62] | Unsupported bus protocol is reported | Reference designs with known traces | 5 |
| HIL export | Plant FMUs or fixed-step C | Constructs that need variable steps are refused, with the reason | Bit-exact comparison with the Ingot reference at the fixed step | 4 |
| HIL evidence | Recorded runs attached to a design version | Evidence on an incompatible version does not count toward verification | Provenance checks | 4 |

## Batteries and power electronics

### Cell models

Cell models form a ladder, and each rung states its validity envelope:

| Model | Equations | Speed | Valid for | Phase |
| --- | --- | --- | --- | --- |
| Equivalent circuit (ECM) | OCV(SOC, T) plus R0 and n RC pairs, parameters as tables over SOC, T and current direction | Microseconds per step | Pack and BMS design, drive cycles; within the fitted current and temperature ranges | 4 |
| Single particle with electrolyte (SPMe) | Solid diffusion in one representative particle per electrode plus electrolyte transport | Milliseconds per step | Moderate rates, up to the limit stated by the parameter set's validation data | 4 |
| Doyle-Fuller-Newman (P2D) | Porous-electrode theory: solid diffusion in each particle across the electrode thickness, electrolyte transport, Butler-Volmer kinetics | Tens of milliseconds per step | High rates, gradients across the electrode, plating risk | 5 |
| Thermal coupling | Lumped, or as a heat source Field into Flux 3D thermal | Per thermal model | Pack thermal design | 4 |
| Degradation | SEI growth, lithium plating and loss of active material submodels | Per model | Ageing studies within the parameter set's tested conditions | 5 |

**Decision D-ELX-19:** Cell models are Flux forms and DAEs in Crucible's pipeline. PyBaMM serves as the reference for oracles and parameter sets. *Why:* PyBaMM is BSD-3-Clause and provides SPM, SPMe and DFN models with SUNDIALS-based solvers [42][43]. Implementing the models natively gives AD sensitivities for parameter fitting, Wasm portability and coupling to Flux thermal Fields. *Rejected:* embedding PyBaMM, which would put a Python runtime in evaluation and break browser parity.

Parameter sets are Materials. Each set is a versioned record with provenance (the publication or the user's own characterization data) and the conditions it was fitted under. That range becomes part of the model's `ValidityEnvelope`.

### Pack design

A pack is an Assembly of cell Instances, busbars, interconnects, a BMS board and an enclosure. `std::elx` adds its electrical meaning:

- **Topology.** Series-parallel arrangements (`14s4p`) generate the electrical network automatically. Each cell Instance gets its own model and its own parameter perturbations, so cell-to-cell variation is captured.
- **Busbars and interconnects.** Resistance and current density come from Flux DC conduction on the busbar Bodies. Joule heat becomes a Field for thermal analysis. Weld or bolt contact resistance is an element with stated uncertainty.
- **BMS.** The BMS is a board designed with `std::elx`. Its functions, such as balancing, state-of-charge estimation and protection thresholds, run either as models or as real firmware in the emulator.
- **Thermal.** Cell heat Fields go to Flux conjugate heat transfer with cold plates and coolant channels. Checks cover maximum cell temperature, spread between cells and coolant pressure drop.
- **Safety.** Fuse and contactor coordination by time-current curves; insulation coordination, creepage and clearance by voltage and pollution degree under IEC 60664-1 [unverified edition]; thermal runaway propagation screening with a cell venting heat-release model from published calorimetry data, labelled as screening with its source.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Cell models | Parameter-set Material plus load profile to voltage, temperature and concentration Fields | Operation outside the parameter set's envelope is flagged with the variable that left it | PyBaMM on shared parameter sets [42]; analytic diffusion cases | 4–5 |
| Parameter fitting | Measured data to a fitted parameter set with confidence intervals | Unidentifiable parameters are reported, not fixed silently | Synthetic data from known parameters | 4 |
| Pack network | Series-parallel layout to a `Circuit` with per-cell variation | Inconsistent cell count or orientation is a compile error | Hand-computed pack resistance and capacity | 4 |
| Busbars | Flux DC conduction on busbar Bodies | Current density over limit fails the check | Analytic bar resistance | 4 |
| Pack thermal | Cell heat Fields to Flux conjugate heat transfer | Temperatures outside limits fail checks | Analytic channel cases; golden product 6 flight data | 4 |
| Safety screening | Fuse coordination, creepage, runaway screening | Results labelled as screening | Published coordination examples | 5 |

### Power converters

Converter design reuses circuit simulation, magnetics and thermal analysis:

1. **Topology library.** `std::elx::power` provides buck, boost, buck-boost, flyback, forward, LLC, phase-shifted full bridge, dual active bridge, PFC boost and three-phase inverters as Ingot features. Each returns a `Circuit`, typically parametric in its passives and switches.
2. **Steady-state design.** Averaged models give duty cycle, ripple and part stresses, which become selection constraints for parametric catalog queries (D-ELX-3).
3. **Control loop.** Small-signal models come from averaged-model linearization or from AC analysis of a switching model (a periodic steady state followed by small-signal analysis, phase 5). Loop compensation uses the controls tools, with margins as checks.
4. **Losses.** Conduction and switching losses come from catalog-part curves of on-resistance, switching energy and reverse recovery against current, voltage and temperature. Magnetics losses come from the magnetics design, and every loss becomes a power Field for thermal analysis.
5. **Layout parasitics.** Hot-loop inductance comes from Flux quasi-static extraction on the routed copper and feeds back into switching simulation to predict overshoot and ringing. A check limits switch-node overshoot against the device's rated voltage.

### Magnetics design

Inductors and transformers are designed parts: core, bobbin, winding and insulation geometry built by a magnetics feature, with Bodies for packaging and thermal analysis.

| Quantity | Interactive method | Sign-off method |
| --- | --- | --- |
| Core loss | Improved generalized Steinmetz equation (iGSE) with DC-bias correction; data-driven material models trained on MagNet data where available | Same models, with flux-density waveforms taken from a Flux magnetostatic solve |
| Winding loss | Dowell's 1D model (1966) [unverified citation]; Albach and Lammeraner for round wire and Albach and Ferreira for Litz wire (models MKF implements [53]) | 2D or 3D Flux eddy-current solve of the winding window |
| Inductance and leakage | Reluctance network with fringing (Roshen) and gap reluctance (Zhang) [53] | Flux magnetostatic solve |
| Capacitance | Albach model for winding capacitance [53] | Flux electrostatic solve |
| Thermal | Thermal network | Flux conjugate heat transfer |

The MagNet Challenge 2023 was an open benchmark for data-driven power-magnetics models. Its results, published in 2025, report that the competition greatly improved model accuracy and reduced model size [39]. Crucible adopts its dataset and metrics as the core-loss benchmark.

OpenMagnetics MKF is MIT-licensed [53] and is a candidate for direct reuse of its model implementations, ported to Rust or compiled to a Wasm component, after a technical review.

Magnetics outputs are catalog-part facets for designed parts. The winding specification, core, gap and insulation system export as a manufacturing drawing and a BOM, so a custom transformer gets an item number and a BOM line like any other Part.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Topology features | Parameters to `Circuit` with selection constraints | Infeasible operating point (duty cycle above the limit) is a typed error | Textbook steady-state equations | 4 |
| Loss and thermal | Loss Fields from part curves and magnetics into Flux thermal | Missing loss curves are listed and the check is unverified | Calorimetric efficiency measurement of golden product 6 converters | 4 |
| Loop design | Small-signal model to compensator and margins | Unstable loop fails the check with the margins | Analytic averaged-model cases | 4 |
| Layout parasitics | Hot-loop inductance from Flux extraction | Unextracted loops are listed | Analytic loop inductance; double-pulse measurements | 4 |
| Magnetics design | Core, winding and gap to losses, inductances and Bodies | Saturation at peak current fails the check | MagNet data [39]; Dowell analytic cases; Flux solves | 4 |

## Wire harnesses

Mechanical (MEC) owns the 3D routing of harness bundles through the product: paths, clamps, bend radii and bundle diameters. This tab owns the electrical side.

- **Connectivity.** A harness is a `Circuit` whose elements are connector, wire, splice and terminal catalog parts. Wires are Instances with gauge, insulation, colour and length. System-level connectivity between boards is ordinary `connect` statements between board ports, so the harness and the boards they join form one netlist.
- **Wire lists.** A query over the harness `Circuit` produces a wire list (from-to, gauge, colour, length, terminals and seals) per variant.
- **Lengths.** Wire lengths come from MEC's routed bundle paths plus service loops and termination allowances, so wire lengths update when the routing changes.
- **Electrical checks.** Wire gauge against current with bundle derating, voltage drop, connector pin current ratings, terminal and wire gauge compatibility, seal compatibility, and shield termination.
- **Formboards.** A formboard is a 2D drawing derived by flattening MEC's 3D bundle topology. It preserves branch lengths and assigns branch angles by a planar layout that avoids overlaps. Drawings include connector tables, wire lists and clip positions.
- **Exchange.** VEC is published as VDA recommendation 4968 and prostep ivip recommendation PSI21; its current version is 2.2.0, and VEC 1.1.2 incorporated features introduced in KBL 2.4 [22]. Crucible reads and writes VEC 2.2.0 and reads KBL 2.4 [unverified current KBL version].

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Harness connectivity | Harness `Circuit` joined to board ports | Pin mismatch is a compile error | ERC corpus | 4 |
| Wire list and lengths | Query over the circuit plus MEC routes | Missing route makes the length unknown and fails the check, never 0 | Hand-checked golden harness | 4 |
| Gauge and drop checks | Current from circuit simulation or declared loads | Violation with the required gauge | Hand-calculated cases | 4 |
| Formboard | Flattened 2D drawing from 3D topology | Overlaps reported | Branch-length preservation property test | 5 |
| VEC and KBL | VEC 2.2.0 read and write; KBL read | Unmapped elements listed | Schema validation; round trip | 5 |

## Robotics

Robots are Assemblies with joints. Mechanical (MEC) owns mates, joints and multibody dynamics. This tab adds actuators, sensors, controllers and the exports robot software needs.

### Kinematic chains

A kinematic chain is a view of an Assembly: links are Parts or sub-Assemblies, and joints are MEC mates with joint type, axis, limits, damping and friction. `std::elx` attaches actuators (motor, gearbox and drive models), sensors (encoders, IMUs, force-torque sensors and cameras) and transmissions to joints. Inertial properties come from the Bodies and Materials, never typed by hand, so they stay consistent with the geometry.

### Export formats

| Format | Contents | Notes | Phase |
| --- | --- | --- | --- |
| URDF | Links, joints, inertials, visual and collision meshes, transmissions and ros2_control tags | Tree structure only, so closed loops are cut with a reported mimic or constraint workaround | 4 |
| SDFormat | Worlds, models, sensors, plugins and closed loops | SDFormat 1.12 [unverified latest version] | 4 |
| MJCF | Bodies, joints, actuators, tendons, sensors, contact parameters | MuJoCo is Apache-2.0 [24]; MJCF can also be produced from SDFormat with sdformat_mjcf [25] | 4 |
| USD | Visual and physics schemas for simulators that consume USD | Via an `io/` USD writer; SDF and USD conversion tools exist (gz-usd) [25] | 5 |

Collision geometry is generated as convex decompositions with a stated Hausdorff error bound, or as primitive fits with the same kind of bound. Visual meshes come from Anvil tessellation with a chord tolerance. Exports carry a Crucible version hash, so a robot description can be traced back to its design commit.

### ROS 2 and simulators

- **ROS 2.** Kilted Kaiju is a standard release supported until November 2026, and the May 2026 release is named Lyrical Luth [23]. Crucible generates a description package per robot (URDF or xacro, meshes, ros2_control configuration, launch files) for the current LTS distribution [unverified which distribution is LTS in October 2026]. Packages build with colcon in CI on Linux.
- **Simulators.** MuJoCo runs in the out-of-process simulation host, linked there through its C API, which its Apache-2.0 licence permits [24]. It serves fast contact-rich simulation and controller tuning. Gazebo runs as an external process through SDFormat, and CI tests every export by loading it in both.
- **Motion planning.** A planning hook interface sends the kinematic model and a collision world (Bodies from the design) to an external planner, such as MoveIt or OMPL, and receives trajectories as `Field<TimeSpan, JointState>`. Planned trajectories become inputs to multibody and drive simulation, so motor torque, current and temperature along a trajectory are checked against limits.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Kinematic chain view | Assembly with MEC joints to links, joints and attached `std::elx` models | A joint without limits or an actuator is reported where the export needs it | Mass properties against Anvil | 4 |
| URDF, SDFormat, MJCF export | Chain to files with stated mesh error | A closed loop in URDF is cut, and the cut is reported | Files load in MuJoCo and Gazebo without warnings; round trip through sdformat_mjcf [25] | 4 |
| ROS 2 description package | Chain to a colcon-buildable package | A failed build is reported with the log | colcon build in CI | 4 |
| Planning hooks | Model and collision world out, `Field<TimeSpan, JointState>` back | A planner failure is returned as a typed error with the planner's message | Recorded planner sessions | 5 |
| Trajectory checks | Trajectory to torque, current and temperature checks | Limit exceedance fails with time and joint | Analytic single-joint cases | 4 |

## RF: antennas and matching networks

Antennas are geometry, so they are Bodies: copper on the board, stamped metal, flex antennas or conductive coatings on the enclosure. Flux solves Maxwell's equations on them. `std::elx::rf` provides the antenna features, ports, matching synthesis and checks.

### Antenna design and analysis

- **Parametric antennas.** `std::elx::rf` provides patch, inverted-F, PIFA, monopole, dipole, loop, helix, slot and array features. Each returns Bodies plus a port definition. Board antennas are layout items on the stackup, so their copper, keepouts and ground clearance obey DRC.
- **Full-wave analysis.** Flux's frequency-domain solver computes input impedance, S-parameters, radiation and total efficiency, gain patterns and isolation between antennas. This tab requires Flux to match the reference capability set of Palace (Apache-2.0): high-order finite elements, an adaptive fast frequency sweep, driven, eigenmode and transient problems, and GPU support [33]. openEMS (EC-FDTD) is GPL-3.0 [32], so it serves only as an external cross-check.
- **Context.** The enclosure, battery, display and harness are in the same model, so an antenna is always analysed in its housing. Plastic permittivity and loss come from the Material record. A missing frequency-dependent property is an error, never a silent default of εr = 1.
- **Validity.** Results carry Flux's error estimate from adaptive refinement. A port whose reference ground is ill-defined, or a far field computed from a too-small radiation boundary, is flagged with the fix.
- **Screening, not compliance.** Specific absorption rate and radiated-power limits are evaluated only as screening estimates with phantom models; the report says so.

### Matching networks

1. **Synthesis.** From the antenna's port S-parameters over the band, `std::elx::rf` synthesizes L, Pi, T and multi-section networks. Broadband problems use real-frequency methods, and the reported Bode-Fano limit shows when the requested bandwidth is physically impossible.
2. **Real parts.** Part values snap to purchasable catalog values. Vendor S-parameter models of the actual inductors and capacitors replace ideal elements, and pad parasitics come from a Flux extraction of the matching footprint.
3. **Yield.** Monte Carlo over part tolerances and antenna detuning by hand or enclosure variation gives return-loss yield across the band, as a check.
4. **Output.** An edit Proposal adds the network to the `Circuit`, with a layout fragment for the matching pads.

### RF circuits

Linear RF analysis (gain, noise figure, stability factors, Smith chart views) runs on S-parameter networks in phase 4. Nonlinear RF analysis (harmonic balance for mixers and power amplifiers, compression and intermodulation) arrives with periodic steady state in phase 5.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| Antenna features | Ingot features returning Bodies and ports | Geometry outside a feature's design range is a typed error | Feature tests | 4 |
| Full-wave antenna analysis | Bodies, Materials and ports to `Field<FreqSpan, SParams>`, far-field Fields and efficiency | Under-resolved mesh or missing material data is flagged, with the fix | Thin-wire half-wave dipole impedance near 73 + j42.5 Ω; cavity-model patch resonance; Palace cross-check on reference geometries | 4 |
| Matching synthesis | S-parameters and band to `Circuit` edits | Infeasible match reports the Bode-Fano bound | Analytic L-network cases; measured boards from golden product 6 | 4 |
| Linear RF circuit analysis | S-parameter network analysis | Non-passive data is flagged | Textbook amplifier examples | 4 |
| Harmonic balance | Periodic steady state with many tones | Divergence reported | Published mixer and PA benchmarks | 5 |

## System modeling and traceability

### SysML v2 status

OMG announced on 21 July 2025 that SysML v2.0, KerML 1.0 and the Systems Modeling API and Services 1.0 were approved for final adoption [2]. The OMG specification page lists SysML 2.0 as a formal specification, published September 2025 [3]. The release repository states that the specifications were formally adopted as of 30 June 2025 and editorially updated in March 2026 for submission to ISO [31].

The repository's software and model libraries are EPL-2.0 [31], and OMG notes that a conformance test suite is still under development [2].

**Decision D-ELX-20:** The system model is native Ingot, built from `std::sys` types that mirror SysML v2 concepts: part and port definitions, connections, requirements, actions, states, constraints, allocations and variation. SysML v2 is a first-class exchange format through its textual notation and the Systems Modeling API, with a semantic mapping specified per concept. *Why:* one language keeps "one model, three editors" intact, and requirements can then reference real Parts, nets and Checks with type-checked units. SysML v2's textual notation and REST API make faithful exchange practical. *Rejected:* SysML v2 as a second authoring language beside Ingot, which would create two sources of truth; SysML v1 XMI exchange, which loses semantics.

Crucible writes its own SysML v2 parser and serializer in Rust from the published grammar, so exchange runs as a Wasm component on every platform. The pilot implementation, with Eclipse and Jupyter installers in the release repository [31], is the reference. Concepts without an Ingot equivalent are preserved as opaque annotations on import and written back unchanged on export, so a round trip through Crucible never drops a foreign model's content.

### Requirements, architecture, physical design and checks

```
use std::sys::{requirement, verify, satisfy, allocate}

requirement flight_time {
    id: "SYS-012"
    text: "Hover endurance at sea level with nominal payload is at least 25 min."
    param endurance: Time >= 25min
    method: analysis + test
}

let hover = hover_endurance(drone, payload: 250g, air: isa(sea_level))
verify(flight_time, by: hover.require(hover.endurance >= flight_time.endurance))
satisfy(flight_time, by: [drone.pack, drone.propulsion])
allocate(functions.power_distribution, to: drone.pdb_board)
```

- **Links are typed references.** `satisfy`, `verify`, `derive` and `allocate` point at Instances, Checks, nets or requirements through `Query`s. They resolve on every build; a broken link is a `ResolveError`, not a dangling row in a spreadsheet.
- **Status is computed.** Each requirement's status follows from its checks: verified, failing, unverified (no check), verified only outside a validity envelope, or waived with a reason. Test evidence (HIL runs and physical tests) counts as verification only when it is attached to the same design version or a declared compatible one.
- **Impact is computed.** Changing a requirement parameter re-evaluates only the checks that depend on it, through Kiln. A Proposal shows the change in requirement status next to the geometry and metric diffs.
- **Exchange.** ReqIF import and export, through an `io/` Wasm component, connect to requirement-management tools [unverified ReqIF version]. Imported requirements keep their external ids.

### Software and firmware as BOM items

A product release names the exact firmware and software that ship with it. This tab defines how firmware binds to hardware. `repo` defines the BOM line (see Contract change requests).

1. **Software item.** A software item has an item number, a version, the content hash of each binary (ELF, bitstream or package), the source repository and commit, the toolchain identity, and a software bill of materials in SPDX or CycloneDX [unverified versions].
2. **Binding.** A `load` relation binds a software item to a programmable Instance, such as a microcontroller, FPGA or flash memory, per variant. The BOM lists the software item under the assembly that is programmed.
3. **Hardware contract.** Crucible generates a board description from the `Circuit`: pin assignments, peripherals, clock sources and memory map. It emits a Zephyr devicetree overlay or a Rust board-support crate. Firmware declares the board-description hash it was built against, and a check compares it with the current board, for example: "Firmware 1.4.2 expects the status LED on PA5; board revision C routes it to PB3."
4. **Reproducibility.** CI rebuilds firmware in a pinned container and compares hashes. A mismatch fails the release check, because an unreproducible binary cannot be traced to its source.
5. **Release.** A signed release records board revisions, software item versions and their compatibility matrix. Field updates are new software item versions against the same hardware, released through `repo` change orders.

| Capability | Contract | Failure behavior | Oracle | Phase |
| --- | --- | --- | --- | --- |
| `std::sys` modeling | Requirements, architecture, functions, allocations as Ingot values | Broken links are `ResolveError`s | Type and resolution tests | 3 |
| Computed requirement status | Status from checks and evidence | Evidence on an incompatible version is excluded, with the reason | Seeded status corpus | 3 |
| SysML v2 import and export | Textual notation and API to and from `std::sys` | Unmapped concepts are kept as opaque annotations | Round trip of the pilot's example models [31] | 4 |
| ReqIF exchange | Requirements with external ids | Unmapped attributes kept as annotations | Round trip of sample files [unverified] | 4 |
| Software items | Binaries with hashes, SBOM and `load` bindings | Board description mismatch fails the release check | Seeded mismatch corpus | 3 |
| Firmware reproducibility | Pinned-container rebuild and hash comparison | Mismatch fails the release | Reproducible reference firmware | 4 |

## State of the art

Commercial tools named as targets (Cadence Allegro and Sigrity, Siemens Xpedition and HyperLynx, Zuken CR-8000 and E3.series, Ansys and JMAG for machines, Dymola and Simulink for system models) are named from general industry knowledge. Their documentation was not opened in this round, so no claim about their internals is made [unverified]. Every number marked as a target is a target, not a result.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Connectivity capture | Drawn schematics with ERC (KiCad 10 [1]); code capture with constraint-solved part picking (atopile [4]) | Altium, KiCad 10, atopile | Code as source, stored drawn view (D-ELX-1) | Scripted concurrent-edit branch pairs, target 100% merged without manual conflict when edits touch different nets; ERC corpus recall, target 100% |
| Land patterns | IPC-7351B tolerance-driven land patterns [55] | KiCad: over 78% of footprints generated from data [1] | 100% generated for standard packages | Pad geometry against an independent IPC-7351B calculation on 2,000 packages; target ±1 µm |
| Automatic placement | Analytical placement with net-crossing and orientation relaxation (Cypress, ISPD 2025 [5]) | Cypress [6]; Allegro X AI [40]; Quilter [41] | Cypress formulation plus height, thermal, decoupling and critical-net terms | Cypress open suite: wirelength, crossings, routability [5]; target: match published Cypress results |
| Interactive routing | Push-and-shove with walkaround, spring-back and optimization (KiCad PNS [45]) | KiCad 10; Allegro; Xpedition | Same structure on exact integer geometry with delay-aware costs | Replayed sessions; target under 16 ms per update with 50 shoved items |
| Autorouting | Negotiated congestion plus gridless detailed routing; learned routers still trail rule-based ones (PCBWorld [30]) | Freerouting [35]; commercial autorouters | Search-based Wasm router with learned cost hints (D-ELX-10) | PCBWorld-Bench eight metrics [30]; target: higher completion and fewer vias than Freerouting at equal or lower runtime |
| DRC | Incremental, spatially indexed, exact predicates | Altium, Allegro, KiCad | Tiled integer DRC cached by Kiln | Seeded corpus with exact rational reference; target 10 s full and 50 ms incremental |
| Delay tuning | Time-domain constraints with per-layer profiles (KiCad 10 [1]) | KiCad 10; Allegro | Field-solved delay with tolerance propagation | Predicted against measured TDR delay on golden-product coupons; target ±2% |
| Cross-section RLGC | 2D quasi-static field solution with roughness and causal dielectrics | Polar Si9000, HyperLynx [unverified] | Flux 2D solve, cached per cross-section | Conformal-mapping stripline and CPW solutions; measured coupons; target ±3% on Z0 |
| S-parameter macromodels | Vector fitting with passivity enforcement [52] | SINTEF Matrix Fitting Toolbox [52] | Rust VF with Hamiltonian check and residue perturbation | Measured Touchstone corpus; target: 100% passive after enforcement, with fit error equal to or below the SINTEF toolbox on the same data |
| Channel simulation | Statistical eye plus bit-by-bit with IBIS-AMI [20][21] | Sigrity, HyperLynx [unverified] | Both modes; AMI in an out-of-process host | IEEE 802.3 channel operating margin reference channels [unverified]; vendor AMI examples; target: eye height within 5% of a commercial tool on shared channels |
| PDN impedance | Plane-pair cavity models with via coupling; full-wave for sign-off | Sigrity PowerSI, HyperLynx PI [unverified] | 2.5D Helmholtz solve in Flux; full-wave fallback | Analytic cavity resonances, target ±2%; VNA measurement on golden product 5, target ±15% |
| IR drop | DC conduction FEM with thermal coupling | Sigrity PowerDC [unverified] | Flux thin-sheet conduction with Aitken-relaxed thermal loop | Analytic strip and annulus resistances, target ±1%; four-wire measurement on golden boards, target ±5% |
| Full-wave EM | High-order FEM with adaptive frequency sweep (Palace [33]) | Palace [33]; openEMS as FDTD reference [32] | Flux frequency-domain solver | Analytic dipole, cavity and patch; Palace cross-check; target: resonance within ±1% of Palace at equal or lower runtime |
| Circuit simulation | MNA, Newton with homotopy, BTF sparse LU | VACASK, fastest open engine by its authors' benchmark [9]; ngspice, broadest compatibility [7] | Rust engine as Flux operations (D-ELX-13) | C6288 runtime ratio against VACASK, target 1.2×; ngspice regression corpus |
| Compact models | Verilog-A compiled to OSDI (OpenVAF [10]) | OpenVAF with ngspice or VACASK | Own Verilog-A front end to Flux kernel IR (D-ELX-14) | BSIM4, PSP and VBIC I-V and C-V curves against OpenVAF-compiled references; target relative 10⁻⁶ |
| Reliability prediction | FIDES 2022 physics-of-failure-informed models [59] | Commercial prediction tools covering SR-332 Issue 4 and FIDES [58] | All four handbooks plus physics of failure | Handbook worked examples; target: equal to printed precision |
| Electric machines | Transient FEM with motion and loss models | Ansys, JMAG [unverified]; Pyleecan with FEMM [44] | Flux magnetostatic maps plus transient sign-off (D-ELX-16) | TEAM workshop benchmark problems [unverified]; dynamometer data from golden product 6; target ±5 points efficiency |
| Magnetics core loss | Data-driven models from the MagNet Challenge [39]; iGSE | OpenMagnetics MKF [53] | iGSE plus MagNet-trained models | MagNet dataset and its error metric [39]; target: no worse than the published winning models |
| Battery cells | DFN (P2D) and SPMe with SUNDIALS solvers | PyBaMM [42][43] | Native forms and DAEs with AD (D-ELX-19) | Agreement with PyBaMM on shared parameter sets; target 1 mV RMS on 1C discharge |
| Multi-domain lumped DAE | Acausal modeling with index reduction and tearing (Modelica tools; ModelingToolkit [51]) | Dymola, OpenModelica [unverified] | One `Circuit` network for all lumped domains (D-ELX-15) | Modelica Standard Library examples via FMU [61]; target: trajectories within the examples' reference tolerances |
| Control design | Riccati, structured H∞, conic MPC | MATLAB Control System Toolbox [unverified] | Rust on faer; MPC through Clarabel [49] | Closed-form cases, target relative 10⁻⁹; Maros-Meszaros QP set [unverified] |
| Co-simulation | FMI 3.0 with clocks and events; SSP 2.0 [12][13] | Simulink, Dymola [unverified] | Deterministic master with out-of-process FMU host (D-ELX-17) | Reference FMUs; coupled-oscillator benchmarks; target: coupling error within the predicted bound in 100% of cases |
| Firmware-in-the-loop | Instruction-level emulation of unmodified binaries with peripheral models | Renode [28]; QEMU | Renode with lock-step circuit coupling (D-ELX-18) | Repeated-run trace identity; reference firmware; target: identical traces in 100% of repeated runs |
| Harness data | VEC 2.2.0 [22] | Zuken E3.series, Capital [unverified] | Harness `Circuit` with VEC exchange | VEC schema validation and round trip; target: zero dropped elements |
| Robot descriptions | URDF, SDFormat, MJCF with converters [24][25] | Hand-written descriptions; CAD exporters [unverified] | Generated from the Assembly with stated mesh error | Mass properties equal Anvil's to 10⁻⁹ relative; files load in MuJoCo and Gazebo |
| System modeling | SysML v2 with KerML and the API [2][3][31] | SysML v2 pilot implementation [31] | Native `std::sys` with SysML v2 exchange (D-ELX-20) | Round trip of the pilot's example models; OMG conformance suite when published [2] |
| Matching networks | Real-frequency broadband matching; Bode-Fano bound | RF circuit tools [unverified] | Synthesis with real-part snapping and yield | Analytic L-networks, target exact to 10⁻⁶; Bode-Fano bound never exceeded |
| Fabrication outputs | Gerber 2026.05 with X2 and X3 attributes [15]; IPC-2581C [19] | KiCad, Altium | Deterministic writers with independent re-readers | 1 µm XOR comparison; target: byte identity across Tier 1 platforms |

## Platform notes

- **Integer geometry everywhere.** Layout coordinates, DRC, fills and fabrication outputs use integer arithmetic. Results are therefore bit-identical across all Tier 1 platforms, which is stronger than the platform-class rule. Golden-board Gerber files must hash identically on every Tier 1 platform in CI.
- **Arc discretization.** Where arcs become chords (fills, Gerber regions, meshes), chord points come from Crucible's own correctly rounded trigonometric routines, never the platform libm, so they are identical on every platform.
- **Text on copper and silkscreen.** Fonts for fabrication come from bundled stroke and outline fonts rendered by Crucible's own code, never by the operating system. Otherwise text geometry would differ by platform.
- **Native third-party binaries.** IBIS-AMI models, FMU binaries, Renode, QEMU, Verilator models, MuJoCo, Gazebo and the ngspice reference run in out-of-process hosts. Vendors often ship AMI models and FMUs only for Windows and Linux on x86-64 [unverified as a general claim]; when the local platform lacks a binary, a Linux x86-64 worker runs it and the result is labelled with that host.
- **Emulator packages.** Renode publishes packages for Linux, macOS on Apple silicon and Windows [28]; its ARM64 Linux and Windows status is [unverified].
- **Robot simulators.** MuJoCo's prebuilt binaries cover Linux on x86-64 and AArch64, Windows on x86-64 only, and macOS [24]. Windows on ARM64 therefore needs a source build or a worker run; the release CI builds MuJoCo from source for that target [unverified build support].
- **Browser.** Every Crucible-native analysis compiles to Wasm and runs in the browser. Native-binary runs go to a team server or cloud worker through `api`; CAS shares their cached results, so the browser shows the same results. With no server reachable, those runs are unavailable and the UI says why (CCR-3).
- **Browser memory.** wasm32's 4 GB address space limits in-browser fills and DRC on very large boards [unverified memory64 status]. Tiles are streamed, and oversized boards go to a worker running the same code.
- **GPU paths.** The placer, Monte Carlo batches and Flux solves use wgpu compute with a CPU fallback. Reductions run in a fixed order, so results match within a platform class. Placement runs are edits rather than evaluations (D-ELX-8), so cross-class differences never change a build.
- **Hardware access.** Firmware flashing and bench adapters need USB and serial access, which live in the `apps/` shells and the platform layer. Browsers use WebUSB and WebSerial where available (Chrome and Edge) [unverified for Safari and Firefox]. Elsewhere, a small local adapter program connects to `api`.
- **Accessibility.** Schematics, netlists, rules and DRC results are exposed as navigable trees through each OS's accessibility API. Circuits are code, so a screen-reader user can capture and review a complete design in the code editor.

## Interfaces with other subsystems

### What this tab provides

| Item | Type | Consumers |
| --- | --- | --- |
| `std::elx` types: `Circuit`, `Net`, `Pin`, `Port`, `Stackup`, `Footprint`, `Schematic`, `Layout` | Ingot types and data modules | All tabs; UIX editors; AGT |
| Bare board | `Part` (kind `pcb`) with Body derived from `Stackup` and outline; flat and folded views | MEC (fit, structural), MFG (fabrication), `io/` (STEP AP242) |
| Assembled board | `Assembly` of the bare board and catalog-part Instances | MEC, MFG, `repo` BOM |
| Part power | `Field<Body, Power>` per Instance, labelled by source (simulated, declared or datasheet) | FLX thermal; MEC thermal-structural |
| Copper current density | `Field<Body, CurrentDensity>` on copper Bodies | FLX electromagnetics and Joule heating |
| Lumped models | `Circuit` elements for motors, drives, cells, packs and sensors with domain-typed ports | MEC multibody and drivetrains; controls |
| Robot descriptions | URDF, SDFormat and MJCF files generated from Assemblies | Robotics users; ROS 2; simulators |
| Fabrication and assembly data | Gerber X2 and X3, drill, IPC-2581, IPC-D-356, ODB++, pick-and-place, BOM views per variant | MFG |
| Requirement links and status | `std::sys` requirements, `satisfy`, `verify`, `allocate`, computed status | Every tab; `repo` releases; UIX review |
| Software binding | Software items bound to programmable Instances by `load` | `repo` BOM and releases |

### What this tab requires

| From | Requirement | Canonical form |
| --- | --- | --- |
| Ingot (ING) | Builder blocks (`circuit { … }`) with idempotent accumulation; domain-typed ports with across and through semantics checked at compile time; a `Variant` enum parameter usable in `match` and `fitted`; data modules (`Schematic`, `Layout`) with a canonical line-per-item format for diff and merge | Language features |
| Ingot (ING) | `Tol<T>` carrying a distribution and correlation group, so Monte Carlo samples parts from the same reel together | `Tol<T>` extension |
| Anvil (ANV) | One integer planar engine with exact arcs (Booleans, offset, Minkowski with a disc, distance predicates), published as the crate `anvil-planar`. The same crate backs Anvil operations and compiles into the DRC, fill and router Wasm components, so both paths give identical results | `anvil::planar_boolean@1`, `anvil::planar_offset@1` (names proposed) |
| Anvil (ANV) | Bend map for flex regions with a neutral-axis offset, returning history records | `anvil::bend@1` (name proposed) |
| Anvil (ANV) | Convex decomposition with a Hausdorff bound; tessellation with chord tolerance; STEP import for catalog-part bodies | Operations with `ErrorBound` |
| Flux (FLX) | Weak forms on 2D and 2.5D Bodies (cross-section electrostatics and eddy currents, plane-pair Helmholtz, thin-sheet conduction), written in Ingot by `std::elx` | Flux form language and `solve` |
| Flux (FLX) | Full-wave frequency-domain solver with lumped and wave ports, far-field transform and adaptive frequency sweep; error estimate per port | Flux operation set |
| Flux (FLX) | Magnetostatics and magnetodynamics with motion (sliding interface or mortar), eddy currents and hysteresis-aware loss post-processing | Flux operation set |
| Flux (FLX) | A network compiler for lumped networks of every domain: flattening, domain checks, Pantelides index reduction, BLT ordering and tearing, residual and Jacobian generation | `flux::compile_network@1` (name proposed) |
| Flux (FLX) | A DAE operation for lumped networks: index-1 DAEs after the network compiler's structural analysis, variable-order BDF and trapezoidal integration, events and breakpoints, adjoint sensitivities | `flux::solve_dae@1` (name proposed) |
| Flux (FLX) | Sparse direct LU with block triangular form and numeric refactorization; complex arithmetic for AC | `flux::solve_linear` variant |
| Flux (FLX) | Operations callable from Wasm components through the host: 2D FFT Poisson solve and batched gradient kernels for the placer, each with wgpu and CPU paths | `flux::poisson_fft_2d@1` (name proposed) |
| Flux (FLX) | A kernel IR that accepts device equations from the Verilog-A front end and emits CPU, GPU and Wasm kernels with AD Jacobians | Shared kernel IR (D-ELX-14) |
| Flux (FLX) | Heat transfer (conduction, conjugate heat transfer, radiation); laminate shells for flex strain; thermomechanical strain for solder fatigue; piezoelectric coupling | Flux operation set |
| Kiln (KLN) | Per-tile caching for DRC and fill; cancellation; results from out-of-process hosts cached with a platform label (CCR-2) | Kiln API |
| Mechanical (MEC) | Enclosure geometry and keep-in volumes; joints, mates and multibody plants with linearization; lumped gear, coupling and bearing models from designed parts; harness bundle routes with lengths | Bodies, Assemblies, `Circuit` elements, route records |
| Manufacturing (MFG) | Capability records: fabricator (materials, via spans, minimum features, panel limits), assembly line, reflow profile, test strategy; DFx feedback channel | Versioned records |
| `repo` | BOM views per variant; non-physical BOM items with content hashes (CCR-4); lockfile pinning of catalog records and parametric resolutions; semantic merge of `Schematic` and `Layout` modules | `repo` API |
| Ecosystem (ECO) | Parts catalog service with versioned records and facets; dated supplier snapshots; licensed data packages kept out of the public registry; translator plugins for proprietary ECAD formats | Registry and catalog API |
| Agents (AGT) | Datasheet extraction workflow with page references; Proposals from placement and routing runs; budget caps for long runs | `api` Propose group |
| UI (UIX) | Schematic and layout editors writing `Schematic`, `Layout` and source edits; constraint manager view; waveform, Smith chart, eye diagram and timeline viewers; 3D board view | Editor contracts |
| Platform (PLT) | Out-of-process hosts for native binaries (FMU, IBIS-AMI, emulators, reference simulators); USB and serial access; remote execution from the browser | Host protocol through `api` |

### External formats

| Direction | Formats |
| --- | --- |
| Read and write | IDX V6 [14]; IPC-2581 Revision C [19]; Touchstone 2.1 and IBIS 8.0 [20][21]; FMI 3.0.2 and SSP 2.0.1 [11][12]; VEC 2.2.0 [22]; SysML v2 textual notation and API [31]; ReqIF; Specctra DSN and SES for external routers |
| Write | Gerber X2 and X3, Gerber job, XNC drill [15]; ODB++ 8.1 [18]; IPC-D-356; pick-and-place CSV; URDF, SDFormat, MJCF [24][25] |
| Read | KiCad projects, libraries and boards; SPICE netlists and libraries; Verilog-A; KBL; IDX baselines from external tools |
| Live bridge | KiCad's IPC API, which uses Protocol Buffers over NNG between a running KiCad and clients [64], for teams that keep some boards in KiCad during migration |

## Oracles

All oracles of this tab live under `oracles/elx/` in the protected directory. Held-out sets are never shown to agents. Loosening any tolerance needs human approval.

| Suite | What it verifies | Reference | Tolerance or criterion |
| --- | --- | --- | --- |
| `connectivity` | Schematic-view edits never change connectivity; connect order never changes the circuit hash; netlist round trips | Property tests (10⁵ random edits per run) | Exact equality |
| `erc` | ERC recall and precision | 300 human-labelled schematics with seeded faults, plus a held-out set of 100 | 100% recall; zero false positives |
| `footprints` | Generated land patterns | Independent IPC-7351B calculation on 2,000 packages | ±1 µm on pad geometry |
| `drc` | DRC verdicts | Seeded violations checked by a slow exact-rational reference checker; metamorphic tests (rotate, mirror, translate the board) | Identical violation sets |
| `fill` | Zone fills | Idempotence, tile-order independence, comparison with an exact reference | Exact equality |
| `router-replay` | Interactive routing | Recorded sessions replayed byte for byte; DRC clean after each commit | Exact equality |
| `autoroute` | Autorouter quality | PCBWorld-Bench metrics [30]; held-out boards; Freerouting baseline [35] | Committed results DRC-clean; targets in State of the art |
| `place` | Placer quality | Cypress open suite [5]; held-out boards | Targets in State of the art |
| `outputs` | Fabrication outputs | Independent re-readers and a 1 µm rasterizer; cross-platform hashes | Zero XOR area beyond arc tolerance; identical hashes on Tier 1 |
| `xsection` | Impedance and delay | Conformal-mapping solutions for stripline and coplanar lines; measured coupons from golden product 5 | ±1% against analytic; ±10% against measurement (target) |
| `macromodel` | Vector fitting and passivity | Measured Touchstone corpus; Hamiltonian passivity re-check | Fit RMS error under the stated bound; passive after enforcement |
| `pdn` | Plane-pair impedance and IR drop | Analytic cavity resonances; analytic strip and annulus resistances; VNA and four-wire measurements | ±2% analytic; ±15% measured (target) |
| `spice` | Circuit simulation | ngspice regression corpus run out of process; textbook analytic circuits | Relative 10⁻³ or absolute 1 µV |
| `va-models` | Compiled compact models | I-V and C-V curves against OpenVAF-compiled references run out of process | Relative 10⁻⁶ |
| `mixed-signal` | Event-driven digital and bridges | Reference waveforms from ngspice XSPICE runs | Event times within one analog step |
| `reliability` | Handbook engines | Published worked examples [58][59] | Printed precision |
| `machines` | Motor maps and losses | Analytic slotless machine fields; TEAM problems [unverified]; dynamometer data from golden product 6 | ±3% torque analytic; ±5% efficiency measured (target) |
| `magnetics` | Core and winding loss | MagNet dataset [39]; Dowell analytic cases | MagNet metric no worse than the iGSE baseline |
| `battery` | Cell models | PyBaMM on shared parameter sets [42]; analytic diffusion cases; cycling data from golden product 6 | 1 mV RMS against PyBaMM (target) |
| `controls` | Control design | Closed-form Riccati and margin cases; generated code against Ingot reference | 10⁻⁹ relative; bit-exact code tests |
| `cosim` | FMI master | Reference FMUs; coupled oscillators with known coupling error | Error within the predicted bound |
| `firmware` | Firmware-in-the-loop | Reference firmware with recorded traces; repeated-run identity | Identical traces per platform class |
| `rf` | Antennas and matching | Half-wave dipole, cavity-model patch, Palace cross-check [33]; Bode-Fano bound | ±2% resonance against reference; bound never exceeded |
| `robot-export` | Robot descriptions | Mass properties against Anvil; files load in MuJoCo and Gazebo | 10⁻⁹ relative; load without warnings |
| `sysml` | SysML v2 exchange | Round trip of the pilot implementation's example models [31] | No dropped elements |
| `determinism` | Cross-platform | Golden boards and analyses on every Tier 1 platform | Integer outputs identical; float outputs within declared tolerance |

## Phasing

| Phase | Deliverables | Gate evidence |
| --- | --- | --- |
| 0, foundations | `std::elx` type skeleton; `anvil-planar` integer predicates in the determinism suite; unit types for electrical quantities including complex values | Determinism suite green on planar predicates |
| 1, wedge | No gate dependency. The circuit-simulation core (operating point, AC, transient) and the lumped DAE pipeline start here because they take longest | None |
| 2, mechanical depth | Lumped rotational and electrical networks, so golden product 3 (gearbox) can be driven by a lumped motor model | Not a gate requirement |
| 3, product breadth | Schematic capture, catalog-part electrical facets, footprint generators, ERC, stackup, manual placement, interactive routing, differential pairs, delay tuning, DRC, fills, through, blind and buried vias, panelization, all fabrication outputs except ODB++, enclosure co-design, impedance, IR drop, board thermal, circuit simulation with Monte Carlo, DFM and DFA checks | Golden product 5: DRC and ERC clean; outputs pass the chosen fabricator's automated DFM check with zero errors, recorded as evidence; measured coupon impedance within ±10% of prediction (target); hottest-part temperature within ±5 K of thermocouple data (target); Gerber hashes identical on Tier 1 |
| 4, full multiphysics | Motors and drives, batteries (ECM, SPMe) and packs, converters and magnetics, controls, FMI and SSP, firmware-in-the-loop, HIL hooks, antennas and matching, EMC screening, SI channels, PDN, microvias and HDI, rigid-flex, IDX, autoplacer and autorouter, ODB++, harness connectivity, robot exports, reliability, `std::sys` traceability | Golden product 6: hover endurance within ±10% of flight test (target); motor efficiency within ±5 points of dynamometer data (target); pack voltage RMS error under 30 mV per cell over the flight profile (target); attitude-loop step response within ±20% of measured overshoot and settling (target); antenna resonance within ±2% of measured (target) |
| 5, electrical depth (proposed) | P2D cells and degradation, periodic steady state and harmonic balance, H∞ and MPC, native Modelica, formboards and VEC and KBL exchange, FMI-LS-BUS, USD export | Proposed golden product: an electric vehicle sub-pack with BMS, harness and charger |
| 6, microsystems and grid scale (proposed) | MEMS electromechanics through Flux coupled solves; utility-scale converters and protection coordination | Proposed golden products: a MEMS accelerometer; a grid-tied inverter |

## Open questions

1. **ODB++ terms.** Siemens says ODB++ interfaces are available at no cost and lists a partner program [18]. Can an open-source writer ship under those terms, and does the contract treat ODB++ as an open standard or a proprietary format?
2. **IPC-2581 revision.** Revision C dates from December 2020 [19]. Whether a later revision has been released could not be verified.
3. **Handbook data.** FIDES guides need registration [59], and SR-332 and MIL-HDBK-217 tables carry their own terms. Which tables may ship in std, and which must be user-supplied licensed packages?
4. **Verilog-A front end.** Writing a Verilog-A front end is a large effort, and OpenVAF is GPL-3.0 [10]. Is a clean-room front end within budget for phase 3, or should phase 3 rely on ported SPICE3 models plus the out-of-process ngspice option?
5. **Renode coverage.** Renode's determinism under multi-core and network models, and its support for ARM64 hosts on Windows and Linux, need verification [28][62].
6. **Learned cost hints.** Training data for routing and placement hints must have licences that allow it. The licence of PCBWorld's board corpus is not stated [30].
7. **Patents.** AI placement and routing is an active patent area. A freedom-to-operate review is needed before the autorouter and placer ship.
8. **Schematic and Layout storage.** D-ELX-1 and D-ELX-6 store drawing and layout as Ingot data modules. If the Ingot tab prefers a separate canonical data format for bulk data, both decisions keep their semantics and change only the file format.
9. **ROS 2 target.** Which distribution is the LTS to target in 2027 needs confirmation from the ROS 2 release schedule [23].

## Contract change requests

- **CCR-1: Fields over time, frequency and parameter domains.** Section 5 defines `Field` over a Body or region. This tab needs waveforms, spectra and sweeps as Fields: `Field<TimeSpan, V>`, `Field<FreqSpan, V>`, `Field<Sweep, V>`, with the same sampling and interpolation-error contract. *Reason:* without this, a parallel "waveform" type appears, which breaks the fewest-concepts rule.
- **CCR-2: Out-of-process results in Kiln.** FMU binaries, IBIS-AMI models, emulators and reference simulators are native code that cannot become Wasm components. Add a third evaluation kind: an external run that is cached, labelled with its host platform class, and excluded from bit-identity guarantees. *Reason:* the contract covers only native operations and sandboxed Wasm components, so these runs need a stated place.
- **CCR-3: Remote execution counts as platform parity.** On platforms without a needed native binary, including the browser, runs execute on a team or cloud worker through `api`. Air-gapped installs need a local Linux worker. *Reason:* "identical features" cannot mean identical local execution of third-party binaries that vendors ship for few platforms.
- **CCR-4: Software items in the glossary.** Add **Software item**: a versioned binary with identity (firmware, bitstream or application) that appears in a BOM and is bound to a programmable Instance by `load`. *Reason:* firmware is not a Body, so it cannot be a Part, yet releases must list it.
- **CCR-5: `Circuit` as a core type.** Add `Circuit` to section 5 as the lumped network type for every physical domain (D-ELX-15). *Reason:* MEC drivetrains, batteries and controls use it. "Magnetic circuit", "thermal circuit" and "hydraulic circuit" are established engineering terms, so the name fits beyond electronics.
- **CCR-6: Interop list.** Add to section 7's interop list: Gerber X2 and X3, IPC-2581, IPC-D-356, Touchstone, IBIS, VEC, SysML v2 and ReqIF as open standards, plus a classification of ODB++ (open question 1). *Reason:* these are the open standards of the electronics domain, and the contract's principle 7 makes open standards first-class.
- **CCR-7: Wasm components may call versioned operations.** Heavy Wasm components such as the placer, the autorouter and the Verilog-A front end need Anvil and Flux operations (planar Booleans, FFT solves, GPU kernels) through a host interface in WIT. Calls are deterministic and are recorded in the component's cache key. *Reason:* section 4 does not say whether a Wasm component can use operations; without it, each component would re-implement geometry and GPU kernels.

## Sources

Pages opened with WebFetch in October 2026. Vendor performance claims are reported as the vendors state them.

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
