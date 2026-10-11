# Interop and ecosystem (ECO)

Crucible reads and writes the open standards of every engineering domain through deterministic translators. Proprietary formats arrive only through licensed translators whose output is pinned. Everything anyone adds, the core team included, ships through one signed registry under an open licence and binding stewardship.

## Scope and translation architecture

ECO owns five things:

1. **Translation.** The `io/` translators, the translation framework, the standards catalog and translator quality.
2. **The Wasm component contract.** Worlds, contexts, capabilities, limits and versioning; PLT owns the determinizer and the runtime (contract section 7.4).
3. **Distribution.** The package registry, catalog-part publishing and the marketplace.
4. **Surfaces around `api`.** SDK packaging, the C ABI, the CLI, events, webhooks and enterprise connectors; AGT owns the method catalog.
5. **Stewardship.** Licensing, governance, disclosure, export and sanctions compliance, trademarks, documentation and migration.

Domain meaning belongs to the owning tab, such as MEC for tolerancing or KLN for lifecycle records. ECO supplies the machinery, sets exchange levels and proves each translator.

| Term | Meaning |
| --- | --- |
| Translator | A reader or writer for one format family: a Wasm component for open formats, an external tool for licensed ones |
| External tool | A native program run out of process in PLT's sandbox; its output enters builds only as External inputs |
| File | A plain value: name, media type and the SHA-256 of bytes in CAS |
| Exchange level | What a format preserves (visual, geometry, structure, semantics or identity), per format and direction |

Three rules run through the tab:

1. The network never reaches evaluation; External inputs do.
2. Nothing is lost silently.
3. Every byte that leaves a tenant leaves through an Act (D-ECO-28).

### Import is a feature

**Decision D-ECO-1:** An import is an Ingot expression over an Asset, evaluated by Kiln like any other feature; no imported state exists outside the program. *Why:* principle 2 forbids GUI-only state, and re-importing a supplier's revision D becomes a one-line change with a geometry diff. *Rejected:* a one-shot native copy, which loses the source. A database of imported objects, which is a second model.

```
use std::io::{read, step}

pub feature motor_mount() -> Assembly {
    let vendor = read("assets/motor_ec45_rev_d.stp", step::options(pmi: semantic))
    vendor.assembly
        .require(vendor.report.lost.is_empty())
        .require(vendor.report.max_deviation < 1um)
}
```

`read` returns `Imported { assembly, parts, bodies, report, source }`, cached under the Asset's hash, the options and the translator version. The statement's `CallSite` comes from source text, so imported names survive a Git round trip.

### Where translators run

| Source | Mechanism | Context | Enters a build |
| --- | --- | --- | --- |
| Open formats | A Wasm component in the `importer` or `exporter` world | Evaluation | As a cached Op output |
| Licensed formats (native CAD, Parasolid, ACIS; JT at first) | An external tool on the vendor SDK, in PLT's translator host | Tool | As an External input in `ingot.lock` |
| Live sources (machines, offers, enterprise systems) | A connector Wasm component | Connector | As an External input in `ingot.lock` |

**Decision D-ECO-2:** Licensed translators never run inside evaluation. Their output enters builds only as External inputs, pinned in the lockfile. *Why:* vendor SDKs are native, closed and not bit-reproducible. Pinning their output keeps builds deterministic and lets anyone rebuild without the licence. *Rejected:* vendor SDKs during evaluation, which break determinism and the browser. A closed binary in the sandbox, which cannot be audited.

The translator host runs with network egress denied (contract section 7.8). A vendor licence server is a named endpoint that an administrator grants. A host with that grant receives only inputs at most `internal` without `controls`, unless a two-person grant names it.

The CAS encoding that licensed tools write is an open specification. A tool anyone can re-run, such as an open-source solver in a pinned container, is an External Op instead (contract section 2).

A build that lacks a needed External input fails with `ExternalInputMissing { asset, translator, options }`. The fix, `crucible import assets/gearbox.CATProduct`, runs the tool and records the result in a Proposal, as a translator upgrade does.

[[DIAGRAM diagrams/11-interop-translation-flow.jsx: translation flow · three sources, one evaluation context]]

Read the diagram top to bottom: open formats stay inside evaluation, and licensed or live sources enter it only as pinned External inputs.

### Translation report

Every read and write returns a `TranslationReport` that Checks read and the UI shows beside the model:

| Field | Content |
| --- | --- |
| `entries` | One per source entity: source id (such as `#1234 ADVANCED_FACE`), outcome and target `EntityId` |
| Outcome | `exact`, `approximated(ErrorBound)`, `healed(ErrorBound)`, `merged(into)`, `dropped(reason)` or `unsupported(construct)` |
| `statistics`, `validation` | Counts by category as CAx-IF reports them; each declared validation property beside Anvil's value |
| `units`, `max_deviation`, `lost`, `diagnostics` | Conversion; largest deviation; dropped entries; typed errors with fixes, including each healing step |

Five rules govern failure:

1. Every source entity appears in `entries`.
2. Recoverable damage skips and reports the instance; `strict: true` fails on the first error.
3. Healing is explicit: `anvil::heal` records each fix with its bound, and `heal: none` disables it.
4. Validation properties beyond the CAx-IF production thresholds raise a `Warning` Check that a design may promote.
5. A writer refuses to drop data: `ExportError` lists what the format cannot carry unless `lossy: allow` is passed.

### Units, axes and identity

Formats that declare units convert to SI with the factor recorded. STL, OBJ and PLY require `units:`, and omitting it is the compile error `MissingUnits`, whose fix lists plausible readings. Axis conventions become a recorded transform: glTF is Y-up, and an OpenUSD stage declares `upAxis` as Y or Z [OpenUSD up axis].

Anvil owns imported identity (D-ANV-31): the source's persistent id, else an exact geometric signature, never an ordinal. When a supplier sends revision D, `anvil::match_bodies` aligns it with revision C in a reviewed `import_map`.

Exports pass through `anvil::exchange_form`, which writes seams and poles per receiver and maps every new entity to its `EntityId`. Writers derive AP242 persistent ids from that map.

The AP242 writer decides semantic PMI per target face. A control on a facet face exports as presentation only, with a report entry, under MEC's eligibility rule.

### Deterministic export

Writers run in the evaluation context, so an export is a cached Op. Three rules make the bytes stable:

1. Header timestamps, such as STEP's `FILE_NAME` time stamp, come from the time `repo` recorded for the Change.
2. Instance identifiers, such as STEP `#n` numbers, follow the canonical order of `EntityId`s.
3. Floating-point values use the shortest decimal text that reads back to the same binary value.

The signed release tag covers a manifest of exported Files and their SHA-256. Stable bytes let the phase 1 gate release reproduce the run build's AP242 and 3MF (contract section 13.1).

Per-recipient watermarking is a deterministic writer transform, `watermark(file, recipient, parameters)`, recorded with each `release_data` commit (D-KLN-40). `crucible verify-watermark` recomputes it, so any recipient's file traces to its release.

### Untrusted content in imported files

1. **Hostile bytes.** Parsers run with fuel, memory and output limits, and every reader is fuzzed continuously.
2. **Hostile text.** Names, notes, PMI text and metadata come back as `ExternalText` with origin (AGT), and entities get neutral identifiers such as `part_017`.
3. **Hostile appearance.** Readers mark every output of an Asset `data_untrusted`, and Kiln joins it into everything derived. A human merge of the import Proposal endorses its typed outputs (contract section 5), while its text stays `ExternalText`. A render of an unendorsed Body is instruction-capable, since geometry can depict text.

Archives (3MF, USDZ, FMU, SSP) are read with limits on entries, expanded size and compression ratio, and a path outside the root fails with `ImportError::UnsafeArchivePath`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `read(path, options) -> Imported` | Pinned Asset to core types, report and header | `ImportError` with a fix | ECO-O-1, ECO-O-17 | 1 |
| `write(model, format, options) -> File` | `Body`, `Part`, `Assembly` or `Field` to a File in CAS | `ExportError` listing what cannot be carried | ECO-O-3, ECO-O-4 | 1 |
| `probe(path) -> FormatInfo` | Format, schema and edition from the first 4 KiB | `Unknown` with the closest matches | ECO-O-16 | 1 |
| Licensed translation | External tool without egress; output pinned | `ExternalInputMissing` | ECO-O-8, ECO-O-15 | 2 |
| Translation report | Every source entity accounted for | A missing entry blocks release | ECO-O-17 | 1 |
| Units and axes | Recorded conversion; `units:` for unitless formats | `MissingUnits` with plausible readings | ECO-O-16 | 1 |
| Imported identity and matching | D-ANV-31 discriminators; reviewed `import_map` | `NoCorrespondence { faces }` (ANV) | ANV-O-NAME-4 | 1 (ids), 2 (matching) |
| Exchange form | Seams, poles, B-spline approximations, id map | `NotRepresentable { faces }` (ANV) | ANV-O-NF-1, ECO-O-24 | 1 |
| Deterministic export | Byte-identical Files everywhere | None at run time | ECO-O-4 | 1 |
| Recipient watermarking | Recorded, recomputable transform | `WatermarkUnsupported { format }` | ECO-O-33 | 3 |
| Untrusted content | Limits, `ExternalText`, integrity until endorsed | `ImportError::LimitExceeded` | ECO-O-5, ECO-O-18 | 1 |

## Standards catalog

### Strategy and exchange levels

Every format gets one strategy:

- **Build:** a Rust Wasm component, generated from a schema where one exists (EXPRESS for STEP and IFC, XSD for XML).
- **Wrap:** a mature open library under a compatible licence, compiled to a Wasm component.
- **License:** a commercial SDK as an external tool (D-ECO-2).

**Decision D-ECO-3:** Open formats are built in Rust as Wasm components and run in the evaluation context on every platform. Each STEP and IFC translator has three layers with separate oracles. Layer 1 is a Part 21 reader and writer generated from EXPRESS, with late-bound access for AP242's long tail; layer 2 holds generated rule checkers. Layer 3 holds hand-written mappings per protocol and CAx-IF practice, the phase 1 critical path. *Why:* every platform runs the same translator, and Anvil alone interprets geometry. Most of a STEP translator is mapping, which EXPRESS does not encode. *Rejected:* wrapping Open CASCADE (LGPL-2.1 with an exception [OCCT licence]), which serves as a differential oracle instead. Per-platform native libraries, which break parity. Early-bound types for all of AP242, which bloat the component. (revised in round 2)

**Decision D-ECO-33:** The repository never vendors ISO schema files. The generator fetches the EXPRESS schemas from ISO's portal by pinned hash, and generated Rust holds only entity and attribute names and types. Before layer 1's first release, the steward asks ISO through ISO/TC 184/SC 4 for written permission to distribute that code under Apache-2.0. If ISO refuses, each organization generates layer 1 from its own copy, and browsers load that build from its team server. *Why:* ISO permits its electronic inserts only "in their original format without any modifications", for its standards' purposes [ISO 10303 portal]. *Rejected:* vendoring the schemas, outside the permission. A hand-written AP242 model, which gives up generation.

`espr`, an Apache-2.0 EXPRESS compiler for Rust, has had no release since 0.4.0 on 20 September 2024 [espr crates.io][espr]. Crucible forks its parser into `io/` and owns the generator.

| Exchange level | Preserved | Example |
| --- | --- | --- |
| Visual | Tessellation, appearance, names | glTF export, OBJ |
| Geometry | Exact B-rep, or a mesh with a stated `ErrorBound` | IGES read, STL |
| Structure | Assemblies, Instances, placements, Part identity, properties, materials by name | AP214 read |
| Semantics | Semantic PMI, kinematics, composites, FE models, connectivity, toolpaths | AP242 with PMI, IPC-2581, QIF |
| Identity | Persistent ids that survive a round trip | AP242 persistent ids, IFC GlobalIds |

Levels are cumulative, and versions were checked in October 2026. A version "at phase n" is fixed in the row's conformance suite (ECO-O-16) when that phase opens. "Owner" defines the data's meaning, and every row shares `read`, `write` and `probe` at its level.

### Mechanical CAD and product data

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| STEP AP242, Part 21 | ISO 10303-242:2025, edition 4 [ISO 242] | R/W | Identity | Build | 1: geometry, structure, properties, PMI write. 2: PMI read, persistent ids. 3: kinematics. 4: composites | ANV, MEC |
| AP242 edition 5 schema; domain model XML | Used in CAx-IF round 58J [CAx-IF 58J] | R/W | Semantics; structure | Build | 3 | MEC; KLN |
| STEP AP203, AP214 | Edition 2; edition 3 [CAx-IF GVP] | R; W | Structure | Build | 1 (R), 2 (W) | ANV |
| STEP AP209 | Extension of AP242 [ISO 10303 wiki] | R/W | Semantics: FE models, results as Fields | Build | 4 | FLX |
| STEP AP238 and ISO 14649 | ISO 10303-238:2022, as MFG states | R/W | Semantics: workingsteps | Build | 3 | MFG |
| STEP AP239; AP233 | At phase 5 | R/W; R | Structure | Build | 5 | KLN; ELX |
| IGES | 5.3 of 1996, the last [IGES wiki] | R/W | Geometry | Build | 2 | ANV |
| JT | ISO 14306-1:2024 [ISO 14306] | R/W | Structure, B-rep, PMI | License [CAD Exchanger formats][HOOPS Exchange], then own reader | 2 (License), 4 (Build) | ANV |
| Parasolid; ACIS | Vendor formats | R/W | Structure, exact geometry | License | 2 | ANV |
| CATIA V5, NX, Creo, SOLIDWORKS, Inventor | Per translator | R | Structure, PMI | License | 2 | ANV, MEC |
| Solid Edge; Rhino | Per translator | R (Rhino R/W) | Structure | License | 3 | ANV |
| PDF; SVG; PDF/A | PDF 2.0; SVG 1.1 Second Edition [SVG 1.1]; PDF/A-4, ISO 19005-4:2020 [PDF/A wiki] | W | Visual: drawing sheets | Build | 1 | MEC |
| DXF; DWG | DXF at phase 2 | R/W | 2D geometry; flat patterns for brakes and cutters | Build; License | 2; 3 | MEC, MFG |

Apart from DWG, Crucible never writes native proprietary CAD formats. Exchange back uses AP242 with persistent ids, which the CAx-IF tests for "ping-pong" iteration [CAx-IF 58J], or licensed Parasolid and JT.

### Mesh, additive manufacturing, scans and buildings

A point cloud is a `Mesh` Body with vertices and no faces, with attributes as Fields.

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| STL | Binary and ASCII | R/W | Geometry; `units:` on read | Build | 1 | ANV |
| OBJ with MTL; PLY | Informal | R/W | Visual; geometry with vertex Fields | Build | 2 | UIX; ANV |
| 3MF | ISO/IEC 25422:2025. Core 1.4.0, Production 1.1.2, Materials 1.2.1, Beam Lattice 1.2.0, Boolean 1.1.1, Secure Content 1.0.2, Volumetric 0.8.0, Toolpath 1.0.0 [3MF specifications] | R/W | Semantics | Build; lib3mf (BSD-2-Clause [lib3mf]) as oracle | 1 (Core, Production, Materials, Beam Lattice), 3 (others; Toolpath once MFG's partner accepts it) | MFG |
| AMF | ISO/ASTM 52915 [AMF wiki] | R/W | Geometry, materials | Build | 2 | MFG |
| glTF 2.0 | ISO/IEC 12113:2022 [Khronos glTF ISO] | W; R | Visual, structure | Build | 2 | UIX |
| OpenUSD | Core Specification 1.0 [AOUSD core 1.0] | R/W | Structure, visual | Build; OpenUSD as oracle | 3 | UIX, MFG, ELX |
| E57; LAS and LAZ | At phase 3 | R/W | Scans, poses, classification | Build | 3 | MEC |
| IFC | IFC 4.3, ISO 16739-1:2024 [ISO 16739][buildingSMART IFC 4.3] | R/W | Semantics of members, plates, openings | Build on the STEP layers | 5 | MEC |

A producer must mark the Beam Lattice extension required, and a consumer without it must refuse the file [3MF beam lattice][3MF core]. So GP2's writer also emits a Core mesh 3MF at a declared chordal error and triangle budget, for the bureau's file-acceptance test (contract section 13.2).

### Electronics

ELX owns the board model, MFG the factory hand-off, and ECO the `io/` readers and writers.

| Format | Version | R/W | Level | Strategy | Phase |
| --- | --- | --- | --- | --- | --- |
| IDF; STEP boards | IDF as KiCad 9 exports it [KiCad 9 PCB editor]; AP242 or AP214 | R | Outline, holes, keep-outs, part heights, designators | Build | 2, early 1.x train |
| IDX | V6.0, December 2025 [prostep IDX] | R/W, incremental | Identity | Build | 2 (baseline import), 4 |
| IPC-2581 | Revision C [IPC-2581C] | R/W | Semantics: stackup, netlist, BOM | Build | 3 |
| ODB++ | ODB++Design 8.1 update 3 [ODB++ 8.1] | R/W | As IPC-2581 | Build; KiCad's writer [KiCad 9.0] as oracle, never linked | 3 |
| Gerber X2 and X3, job file, XNC | Gerber 2026.05 of 19 May 2026; job 2020.08; XNC 2021.11 [Ucamco Gerber] | W; R to verify | Copper, mask, attributes | Build | 3 |
| KiCad files | S-expression formats [KiCad formats] | R; W of libraries | Semantics | Build | 3 |
| EDIF; IPC-D-356; Specctra DSN and SES; placements | EDIF 2 0 0, ANSI/EIA-548-1988 [EDIF wiki]; others per ELX | W (SES R) | Connectivity, routing, placement | Build | 3 |
| Touchstone, IBIS; VEC | 2.1 and 8.0; VEC 2.2.0, per ELX | R/W | Catalog-part models; harnesses | Build | 3; 4 |
| KBL | At phase 5, per ELX | R | Harnesses | Build | 5 |
| SPICE netlists and models; Verilog-A | The ngspice, PSpice and LTspice dialects ELX reads | R | Circuits and device models (D-ELX-14) | Build | 3 |

Proprietary ECAD designs migrate through KiCad's importers (D-ECO-31).

### Simulation and analysis

FLX owns the FMI and SSP runtime (D-FLX-30), and ECO owns FMU packaging, FMI-LS-WASM included; phases follow contract section 13.4.

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| FMI | 3.0.2 [FMI 3.0.2 news], 3.0.3 announced [Modelica newsletter 2026-02]; 2.0.5 for import [FMI site] | R/W | Semantics | Build | 3 (R), 4 (W) | FLX |
| FMI layered standards | LS-XCP 1.0.0, LS-BUS 1.3.0-beta.1, LS-STRUCT 1.0.0-rc.1, LS-REF 1.0.0-beta.1, LS-DAE 1.0.0-alpha.1 [FMI site] | R; LS-BUS W | Kept and reported when unsupported | Build | 4 | FLX, ELX |
| FMI-LS-WASM | Non-normative prototype mapping the FMI C API to WIT [fmi-ls-wasm] | R/W, gated | Portable FMUs | Build; ECO joins the group | 3 (R), 4 (W) | FLX |
| SSP | 2.0.1 [SSP site] | R/W | Structure | Build | 4 | FLX |
| CGNS; Exodus II | CGNS 4.5.2 [CGNS releases]; Exodus from BSD-licensed SEACAS [SEACAS] | R/W | Meshes and solutions as Fields | Wrap (D-ECO-4) | 4 | FLX |
| VTK, VTKHDF | VTKHDF 2.8 [VTKHDF] | W; R | Fields on meshes | Build | 2 | FLX |
| Nastran BDF; Abaqus input | Dialects at phase 3, from FLX's test models | R/W | FE models; OP2 results as Fields | Build | 3 | FLX |
| OpenFOAM case | OpenCFD v2606 [OpenFOAM v2606]; Foundation OpenFOAM 14 [OpenFOAM 14] | R/W | Mesh, conditions, fields | Build; the solver only as an External Op | 4 | FLX, COV |

**Decision D-ECO-4:** Formats built on HDF5 (CGNS, Exodus II, VTKHDF) wrap the reference C libraries compiled to Wasm components. `H5Pset_obj_track_times` switches off time tracking [HDF5 track times], and ECO-O-4 proves the bytes stable. *Why:* HDF5's reference library is its only complete implementation. *Rejected:* a pure Rust HDF5 subset, revisited only if the library blocks determinism. Native libraries, which break browser parity.

### Manufacturing, metrology, systems and materials

| Format | Version | R/W | Level | Phase | Owner |
| --- | --- | --- | --- | --- | --- |
| Tool data | ISO 13399 in vendor packages; the library formats MFG lists | R | Tool Assemblies | 2 | MFG |
| Presetter readings | Per connector | R | Signed External inputs by tool serial | 2 | MFG |
| QIF; inspection results | QIF 3.0, ISO 23952:2020 [QIF site]; a CSV template keyed by balloon label | R/W | Characteristics, plans, results | 1 (results read), 2 (characteristics, plans), 3 | MFG |
| DMIS; MTConnect | DMIS at phase 3; MTConnect 2.5.0 [MTConnect 2.5.0] | W, R; R | Programs and results; machine state as External inputs | 3 | MFG |
| OPC UA for Machine Tools | OPC 40501-1 release 1.02.0 [OPC 40501-1 v1.02] | R; jobs only by `store_machine_job` | Machine state | 3 | MFG |
| ReqIF; SysML v2 and its API | ReqIF 1.2 [ReqIF]; SysML 2.0, KerML 1.0, API 1.0 [OMG SysML v2] | R/W | Requirements; `std::systems` models | 4 | ELX |
| URDF; SDFormat; MJCF | SDFormat 1.12 [SDFormat]; others at phase 4 | W; R | Kinematic trees, inertials, sensors | 4 | ELX |
| MatML; ISO 10303-235 | MatML at phase 2; ISO 10303-235:2019, as COV states | R/W | Property and test records | 2 | COV |
| GDSII; OASIS | At phase 5 | R/W | Mask and package layers (D-COV-9) | 5 | COV, MEC |

All rows here are Build, and Crucible never reverse-engineers a proprietary format. G-code has no `io/` translator: MFG's posts write it through the `post-processor` world (D-MFG-5), and `verify_nc` reads it.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| STEP layer 1: Part 21 | Generated reader and writer; hash-pinned schemas | `ImportError::Unreadable { location }` | ECO-O-23, ECO-O-5 | 1 |
| STEP layer 2: schema rules | Generated checkers on every export | `ExportError::SchemaRule { rule, instance }` | ECO-O-3 | 1 |
| STEP layer 3: AP242 mapping | Geometry, structure, properties, PMI write | Report entries | ECO-O-1, ECO-O-2 | 1 |
| AP242 PMI read, persistent ids, tessellation | Per recommended practice | Report entries | ECO-O-2, ECO-O-24 | 2 |
| 3MF and STL | Beam Lattice marked required; a Core mesh beside it | `ExportError` over the triangle budget | ECO-O-16 | 1 |
| Inspection results import | QIF Results or CSV to one Evidence record per characteristic (MFG) | Unmatched labels reported | ECO-O-16 | 1 |
| Drawing writers | PDF, SVG, PDF/A; DXF; licensed DWG | `ExportError` | ECO-O-3, ECO-O-4 | 1, 2 (DXF), 3 (DWG) |
| Licensed MCAD translators | Mechanical table rows | Unqualified versions flagged | ECO-O-15 | 2 |
| Board exchange for mechanical teams | IDF, STEP boards and IDX to a read-only board Part | `ImportError` naming missing data | ECO-O-26 | 2 |
| Board fabrication and assembly writers | Gerber, XNC, IPC-2581C, ODB++, IPC-D-356, placements | `ExportError` | ECO-O-25 | 3 |
| IDX change proposals | Incremental exchange with responses | Rejected proposals reported | ECO-O-16 | 4 |
| HDF5-based formats | Wrapped library, deterministic writes | `ExportError::Nondeterministic` | ECO-O-4 | 4 |
| Remaining catalog rows | Per table row | Report rules | ECO-O-16 | 2 to 5 per row |

## Translator quality

A translator ships only when independent oracles show it keeps its catalog row's promise. Five layers do this: interoperability testing, validation properties, round trips, differential testing and fuzzing.

### CAx-IF participation

The CAx Implementor Forum belongs to the MBx Interoperability Forum of AFNeT, PDES, Inc. and prostep ivip [MBx-IF]. Round 58J ran from March to September 2026 and covered assembly PMI, composites, kinematics, persistent ids, holes and threads [CAx-IF 58J].

**Decision D-ECO-5:** Crucible joins the MBx Interoperability Forum in phase 1 and takes part in every CAx-IF round, and each round's results become regression oracles. *Why:* the forum is where AP242 implementers agree on practices and find each other's bugs against real CATIA, NX and Creo output. *Rejected:* public sample files alone, which miss current practices. Waiting for a mature translator, which delays the bugs that matter.

Round files enter `oracles/` only where the forum's terms allow; otherwise only Crucible's own results do. The fee is a phase 1 budget line that the founder approves at the phase 0 gate.

### Validation properties and corpora

In the CAx-IF practice, version 4.6, a sender writes validation properties so a receiver can check what it read [CAx-IF GVP]:

| Property | Interoperability testing (green / yellow / red) | Industry production |
| --- | --- | --- |
| Volume, area, curve length | Below 1% / 1–10% / above 10% | 0.5% |
| Centroid | Below 1 mm / 1–5 mm / above 5 mm, or 0.1% / 1% of the box diagonal | 0.02 mm plus 0.1% for models over 20 mm |
| Bounding box | Absolute error of both corners | 0.5% |

Exports write these properties from Anvil's certified integration, and imports check them against the production thresholds. The internal target is 0.05% on volume and area. Round trips and item-by-item PMI comparison cover what properties miss.

**Decision D-ECO-37:** Oracles never vendor third-party datasets; each corpus is a list of content hashes fetched at test time, with licence evidence per item. ABC enters only as contract section 13.3's licence-filtered subset. Its documents show, through the Onshape API, a Free Plan owner, creation on or after 7 August 2018 and no LICENSE tab. The subset serves benchmarks and published measurements; training follows D-AGT-22. *Why:* ABC's models belong to their creators [ABC], and Onshape licenses copying only for those documents [Onshape terms]. *Rejected:* all of ABC "for testing only" (round 2), since copying is itself a use. Vendored corpora, which ship with the repository. The Fusion 360 Gallery dataset, non-commercial only [Fusion 360 Gallery licence].

| Corpus | Contents | Access |
| --- | --- | --- |
| NIST MBE PMI test cases | CTC, FTC, STC and HTC files with native models [NIST MBE PMI] | Public |
| CAx-IF round files | Current-practice files from many systems [CAx-IF 58J] | Participants, under the forum's terms |
| ABC licence-filtered subset | Onshape models with STEP, Parasolid, meshes and FeatureScript [ABC] | Hash list with per-model evidence |
| Held-out corpus; format suites | Models never shown to agents; 3MF, FMU, SSP, IFC and KiCad samples | Protected store; hash lists |

### Round trips, fuzzing and qualification

All topology comparisons use Anvil's topology normal form on both sides (ANV-O-NF-1).

| Suite | Pass line | Phase |
| --- | --- | --- |
| Self round trip | Exact geometry bit-identical, procedural within its stored bound; topology equal; ids and PMI kept | 1 |
| External round trip on CAx-IF ping-pong cases | Properties within thresholds; persistent ids match; edits appear as a diff | 2 |
| Differential read against Open CASCADE 8.0.1 [OCCT releases], later a licensed translator | Topology equal; Hausdorff distance under the larger tolerance; disagreements triaged | 1 |

Open CASCADE runs only as an external oracle in CI. Readers are fuzzed with structure-aware mutators and grammar-based generators, and each release needs 10⁹ executions per reader without a new crash (target).

A licensed translator version is qualified on the NIST and held-out native files before anyone can pin it. A signed record keeps its topology counts, property deviations and PMI statistics, shown beside every External input it produced. Translators are versioned packages, so output changes are labelled (D-ECO-14).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| CAx-IF participation | Every round; results become oracles | A regression blocks release | ECO-O-1, ECO-O-2 | 1 |
| Validation properties | Written and checked | `Warning` Check beyond thresholds | ECO-O-1 | 1 |
| Corpora by hash list | No vendored third-party data; per-item licence evidence | An item without evidence is not fetched | ECO-O-31 | 1 |
| Round trips in normal form | The three suites above | A self round-trip failure blocks release | ECO-O-24 | 1, 2 (external) |
| Reader fuzzing | Continuous, per reader | A new crash blocks release | ECO-O-5 | 1 |
| Licensed translator qualification | Signed record per version | Unqualified versions cannot be pinned | ECO-O-15 | 2 |
| Translator versioning | Output changes labelled; pins re-export identically | Unlabelled changes refused | ECO-O-10, ECO-O-22 | 1 |

## The extension model

### Tiers and contexts

Contract section 4 fixes three tiers: Ingot packages, Wasm components and operations. Wasm components carry importers, nesting, toolpath strategies, specialist solvers, panels and connectors, and anyone contributes an operation through the RFC process.

**Decision D-ECO-6:** Authors choose the tier by a fixed rule. Use a Wasm component only when code needs over about 10⁶ primitive steps per call, an existing codebase, or a data structure Ingot handles poorly. Promote to an operation only when three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux. *Why:* most logic stays in the most reviewable tier. *Rejected:* free choice, which misplaces heavy and trivial code. A native plugin tier, unsafe and absent from browsers.

Process isolation of third-party Wasm components is the one difference principle 1 permits. PLT's call-overhead targets and the batched `crucible:ops` form bound it (contract section 7.4). A Rust `#[ingot::feature]` receives ING's guest context, `ingot_sdk::Cx`; the native `OpCx` never enters a Wasm component.

Wasm components are CPU-only; GPU work lives in operations, which they call through `crucible:ops`.

| Context | Runs | May import | Never imports | Output enters |
| --- | --- | --- | --- | --- |
| Evaluation | Inside Kiln as an Op | `crucible:ops`, `geom`, `field`, `product`, `host`, type-only interfaces | `wasi:`, `crucible:api` | Kiln, under the Op's key |
| Panel | Out of process if third-party | `crucible:api/read`; `edit` when granted | Clocks, randomness, files, network | `api` calls recorded in `ChangeProvenance` |
| Tool | In `apps/tool-runner` | `crucible:api`, `wasi:filesystem` on granted directories, `wasi:clocks`, `wasi:random`, `crucible:tool/process` | Network, except granted endpoints | External inputs, `api` calls |
| Connector | On a team server or desktop | Scoped `crucible:api`, `wasi:http` to declared hosts, `wasi:clocks`, `wasi:random`, `crucible:connect` | Files, processes | External inputs, events, Acts |

The registry checks imports at publish and the host again at instantiation.

An evaluation component reaches engine data only through `crucible:ops` and `crucible:host/cas` reads of objects reachable from its input handles (contract section 4). A raw `ObjectId` resolves to nothing, every read joins the node's label, and measurements are operations, never host calls.

Processes spawned through `crucible:tool/process` run in PLT's sandbox with egress denied (contract section 7.8). A manifest may declare named endpoints, such as a licence server, which an administrator grants and the sandbox enforces by address.

### Isolation and platforms

**Decision D-ECO-26:** Only first-party Wasm components from the hermetic builder run inside the engine process. Every third-party one, a user's unpublished one included, runs in a worker under PLT's OS sandbox, holding no tokens, handles or keys. On servers, workers are per (tenant, confidentiality label), labels with `controls` get dedicated VMs, and pooling slots never cross them. Trusted builders run third-party code only in single-use microVMs (contract section 7.8). *Why:* the engine process holds every open repository, token and device key. Wasmtime's April 2026 advisories include an out-of-bounds write and a pooling leak [Wasmtime GHSA-394w][Wasmtime GHSA-6wgr]. *Rejected:* in-process execution for verified publishers (round 1), since identity is not memory safety. One worker pool for all tenants. (revised in round 3)

PLT applies Wasmtime security releases within 7 days (D-PLT-21), each gated by ECO-O-6.

| Platform | Engine |
| --- | --- |
| Windows, macOS, Linux; servers | Wasmtime LTS with Cranelift in `wasm-host` (PLT) |
| Desktop browsers | The browser's engine through one first-party Wasm component runtime (D-ECO-10) |
| iPadOS | The web build in a WKWebView shell, where JavaScriptCore compiles Wasm; only first-party components in the app run locally (contract section 7.4) |
| Android tablets | Wasmtime, Tier 3 there [Wasmtime tiers]; Play allows downloaded code only with indirect API access [Google Play DNA], so no world imports an Android API |

Tool and connector components run on the server for browsers and tablets. On iPadOS no downloaded code runs (guideline 2.5.2), and packages appear only as design dependencies (3.2.2(i)) [App Review]. Local registry components would first need a 4.7.4 web index, 4.7.1 reporting and 4.7.5 age ratings.

**Decision D-ECO-10:** The registry ships determinized core modules plus a data description of each Wasm component, never per-component JavaScript. One first-party browser runtime lifts and lowers from it. Browsers evaluate third-party evaluation components remotely until the asynchronous bridge passes PLT-O-WASM-1 there (contract section 7.4). Then they run in an `<iframe sandbox="allow-scripts">` from a sandbox site on another registrable domain. Its scripts carry `Content-Security-Policy: default-src 'none'; script-src 'self' 'wasm-unsafe-eval'`, `Cross-Origin-Embedder-Policy: require-corp` and `Cross-Origin-Resource-Policy`, and data cross as transferable `ArrayBuffer`s. *Why:* generated glue would run beside every local repository and key. The sandbox drops storage and credentials, and `default-src 'none'` blocks `fetch` and WebSocket [MDN default-src][MDN connect-src], while `'wasm-unsafe-eval'` admits Wasm [MDN script-src]. *Rejected:* per-component ES modules as jco generates them [jco]. Transpiling in the client. Pulley compiled to Wasm. An opaque-origin worker without a network policy (round 2). (revised in round 3)

PLT owns the web app's integrity: an asset manifest in a transparency log, TUF checks in the service worker, and expiring apt and dnf metadata.

### First-party WIT packages

Each package follows SemVer [WIT guide], and its owner specifies it in a "WIT interfaces" subsection with an oracle that the published WIT matches. This table is the index.

| WIT package | Interfaces | Owner |
| --- | --- | --- |
| `crucible:units` | `si` | ECO, with ING |
| `crucible:ops` | `anvil`, `flux`: async, generated from the operations catalogs, with a batched form | ANV, FLX; ECO generates the bindings |
| `crucible:geom` | `types`, `build` | ANV |
| `crucible:field` | `types`, `build` | FLX |
| `crucible:product` | `types`, `build`, `read` | MEC, KLN |
| `crucible:host` | `diagnostics`, `progress` (write-only), `cas` (handle reads); `parallel` | KLN; PLT for `parallel` |
| `crucible:io` | `types`, `read`, `write`; worlds `importer`, `exporter` | ECO |
| `crucible:physics`; `crucible:material` | `solve`; `model`; worlds `solver`, `constitutive` | COV, FLX |
| `crucible:mfg` | `strategy`, `post`; strategy, post, nesting, packing, slicer and recognizer worlds | MFG |
| `crucible:ui` | `types`, `view`, `canvas-host`, `canvas`; worlds `panel`, `canvas2d` | UIX |
| `crucible:api` | One interface per method group | AGT |
| `crucible:tool` | `process`, `external`; world `driver` | ECO, with PLT |
| `crucible:connect` | `types`, `secrets`, `partner`, `erp`, `mes`, `plm`; one connector world each | ECO, with MFG and KLN |

**Decision D-ECO-7:** Every first-party WIT package uses the `crucible:` namespace, one package per domain, in American spelling. Operations are reached only through `crucible:ops`, with one generated interface per catalog. `crucible:geom` and `crucible:field` hold types and builders, and product structure lives in `crucible:product`. *Why:* one namespace makes ownership obvious, and any other computing interface would bypass recorded Op dependencies. "Model" names a physics model elsewhere. *Rejected:* per-subsystem namespaces such as `flux:`. Operations inside `crucible:geom` (round 1). `measure` and `sample` host interfaces (round 2). The name `crucible:model`. (revised in round 3)

No `crucible:` package freezes before the names clear (contract section 13.1), and examples use `@0.1.0` until then. Units cross as SI `f64`, while the Ingot wrapper carries `Quantity<D>`, and strings a component authors become `ExternalText`.

ECO's own packages:

| Package | Interfaces and main items | Failures | Phase |
| --- | --- | --- | --- |
| `crucible:units` | `si`: one `f64` alias per SI dimension, such as `length` | None; the Ingot wrapper checks dimensions | 0 |
| `crucible:io` | `types` (`source`, `sink`, options, `disposition`, `entry`); `read` (`probe`, `parse`); `write` (`emit` from a read-only `model-view`) | `import-error`, `export-error` | 1 |
| `crucible:tool` | `process` (spawn in PLT's sandbox without egress); `external` (requests to a licensed translator host) | `process-error`, `egress-denied`, `capability-denied` | 2 |
| `crucible:connect` | `types` (offers, quotes, orders); `secrets` (named, host-bound); `partner` (`request-quote`, `place-order`, `get-status`); `erp`, `mes`, `plm` (mapped records) | `partner-error`, `mapping-conflict` | 2 |

### WIT example: an importer

The importer reads an Asset through a random-access host resource, which zip-based formats need, and emits entities through builders, so Anvil decides validity.

```wit
package crucible:io@0.1.0;

interface types {
    use crucible:geom/types@0.1.0.{error-bound, heal-policy};
    use crucible:units/si@0.1.0.{length};

    resource source {                       // the Asset's bytes, supplied by the host
        size: func() -> u64;
        read: func(offset: u64, len: u32) -> list<u8>;
    }
    record format-info { media-type: string, schema: option<string>, edition: option<string> }
    enum pmi-mode { none, presentation, semantic }
    record read-options { units: option<length>, heal: heal-policy, strict: bool, pmi: pmi-mode }
    variant disposition {
        exact, approximated(error-bound), healed(error-bound),
        merged(u32), dropped(string), unsupported(string),
    }
    record entry { source-ref: string, outcome: disposition }
    record read-result { entries: list<entry>, header: list<tuple<string, string>> }
    variant import-error { unreadable(u64), unsupported-schema(string), missing-units, limit-exceeded(string) }
}

interface read {
    use types.{source, format-info, read-options, read-result, import-error};
    use crucible:product/build@0.1.0.{product-builder};
    probe: func(head: list<u8>) -> option<format-info>;
    /// Every source entity must appear in `read-result.entries`.
    parse: func(src: borrow<source>, options: read-options, out: borrow<product-builder>)
        -> result<read-result, import-error>;
}

world importer {
    import types;
    import crucible:geom/build@0.1.0;      // B-rep, mesh and point builders, validated by Anvil
    import crucible:product/build@0.1.0;
    import crucible:host/diagnostics@0.1.0;
    export read;
}
```

The `exporter` world mirrors it, writing from a read-only `model-view` into a `sink` that becomes a CAS blob.

### Capabilities

A Wasm component can call only what its world imports. The manifest scopes each import (hosts, directories, `api` scopes, named secrets), a person grants each scope per package, and `ingot.lock` records it. Organization policy allows or denies publishers, capabilities and licences, and evaluation components need no grants.

**Decision D-ECO-27:** A Wasm component may hold at most one of three capabilities: reads above `public`, network egress, and file writes outside CAS. Only a `policy:admin` grants an exception. Connector `api` scopes never include design reads, and outbound data from labelled reads goes through a `release_data` Act (D-ECO-28). Grant screens state combinations, such as "can read your designs and send data to api.supplier.com". *Why:* two harmless-looking grants combine into an exfiltration channel. *Rejected:* per-capability grants without a flow rule (round 1). Taint tracking inside components, which the sandbox cannot verify.

An update that adds a capability or changes the signer waits as a Proposal. A named secret goes only to its declared host, revoking a grant stops running instances with `CapabilityDenied { capability, package, fix }`, and every tool and connector call is audited.

### Determinism and limits

Contract section 7.4 states the rules, and PLT owns the determinizer and its overhead table. ECO adds three rules:

1. Randomness arrives only as an explicit `seed` argument from an Ingot `Rng` (ING).
2. Limit outcomes follow KLN's one catalog: `FuelExhausted`, `StackExhausted` and `WorkLimit` are cached `Failure`s, and host resource errors and cancellation are Aborts.
3. Data parallelism uses `crucible:host/parallel`, whose combinators return outputs in input order (PLT).

**Decision D-ECO-8:** Evaluation-context Wasm components execute only as determinized binaries. The registry runs PLT's determinizer at publish, the local toolchain runs the same version for unpublished components, and the binary's SHA-256 enters the `OpKey`. *Why:* engine-independent instrumentation gives identical results and trap points everywhere, as `wasm-instrument` and finite-wasm show for metering [wasm-instrument][finite-wasm]. *Rejected:* engine fuel, absent from browsers. Wall-clock timeouts, which are nondeterministic. Instrumenting on each client, a second producer of executed bytes. (revised in round 2)

**Decision D-ECO-9:** Evaluation worlds import no WASI and are deterministic. Their `crucible:ops` imports are Component Model async functions in the callback ABI (contract section 7.4). A host may then answer across a process or agent-cluster boundary. The host delivers completions in issue order, so timing never shows, and fuel never counts host time. Evaluation worlds use no `stream` or `future` types, while tool and connector worlds use WASI 0.3's [WASI 0.3][WIT guide]. *Why:* third-party components run out of process, and the callback ABI returns to an event loop without fibers [CM concurrency]. *Rejected:* synchronous evaluation worlds (round 2), which browsers cannot answer across agent clusters. The stackful ABI, which needs stack switching. Free completion order, which is nondeterministic. (revised in round 3)

Limits apply per call. A manifest may request more, up to the organization's ceiling, and PLT reserves declared memory before instantiation.

| Limit | Evaluation default (ceiling) | Tool and connector default | Outcome |
| --- | --- | --- | --- |
| Linear memory | 256 MiB (4 GiB) | 2 GiB | `memory.grow` past the declared maximum returns −1 and the component decides (PLT); a host-caused failure below it is an Abort |
| Fuel | 5 × 10¹⁰ units, roughly 10 to 30 s native (policy) | Wall-clock budget | `FuelExhausted { used, limit }`, cached |
| Logical stack | 256 KiB (1 MiB, calibrated in phase 0) | Engine default | `StackExhausted { limit }`, cached |
| Output; handles; binary | 2 GiB per output; 10⁷ handles (10⁸); 64 MiB (256 MiB) | Policy; 10⁶; 64 MiB | `WorkLimit { kind, limit }`; large binaries refused at publish |
| Wall clock | None, cancellation only | 15 min per call | The call fails with `Timeout`, never cached |

Work above 4 GiB uses PLT's chunked buffers, operations or server-side tool components. 64-bit memories stay off until every Tier 1 browser engine supports them [Wasm 3.0].

### Versioning

WIT packages follow SemVer with feature gates: `@since` items never change incompatibly, `@unstable` items may vanish, and `@deprecated` pairs with another gate [WIT gates]. Five rules follow:

1. A 1.x package only adds items; unstable features are opt-in and publish only in pre-releases.
2. Deprecation lasts at least 24 months and one edition, and a new major ships an adapter for the old world.
3. Every world major stays executable for 10 years after it is superseded (target).
4. No engine upgrade ships unless every registry test vector's hash is unchanged.
5. The Component Model still evolves through WASI preview releases [Component Model]. If its binary encoding changes, the registry re-encodes stored components, proves identical results and keeps the original hash as identity.

WASI 0.3.0 shipped on 11 June 2026 and 0.3.1 on 11 August 2026, with no date for 1.0 [WASI roadmap]. Wasmtime 46 first implements final 0.3.0 [WASI 0.3]. Only tool and connector components track this train, on the current and previous 0.3.x releases.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Contexts and worlds | Imports checked at publish and instantiation | `ForbiddenImport { import, fix }` | ECO-O-8 | 0 |
| First-party WIT packages | Index; 0.x until names clear | Unstable items need opt-in | ECO-O-6 | 0 |
| ECO's WIT packages | `units`, `io`, `tool`, `connect` as tabled | A differing interface fails release | ECO-O-34 | 0 (`units`), 1 (`io`), 2 |
| `crucible:ops` bindings | Generated async interfaces with a batched form | `OpVersionRetired` with an upgrade | ECO-O-6 | 1 (`anvil`), 2 (`flux`) |
| Data access by handle | `crucible:host/cas` reads only objects reachable from input handles | A raw `ObjectId` resolves to nothing | ECO-O-8 | 1 |
| Process isolation | Sandboxed workers; microVMs on trusted builders | Worker loss is an Abort | ECO-O-8 | 1 |
| Tool egress | No network; named endpoints by grant | `EgressDenied { host }` | ECO-O-8 | 1 |
| Capability grants and flow rule | Scoped grants; at most one risky capability | `CapabilityDenied` | ECO-O-8 | 1 |
| Determinized execution and limits | Contract section 7.4; seeds; KLN's outcomes | Limit `Failure`s cached | ECO-O-6, ECO-O-7 | 0 |
| Browser Wasm component runtime | Generic runtime for first-party components | Missing description fetched remotely | ECO-O-6 | 1 |
| Browser sandbox | Remote until the bridge passes, then the sandboxed iframe | Remote evaluation | ECO-O-8 | 2 |
| Tablet execution | First-party components only on iPadOS | Remote evaluation | ECO-O-6 | 3 |
| WIT versioning | Additive minors, deprecation, adapters, retention | A removal in a minor is refused | ECO-O-10 | 0 |

## SDKs, CLI, events and integration

AGT's method catalog is the only programmatic surface (D-AGT-1); ECO packages it and adds events, exit surfaces and enterprise connectors.

### SDKs, methods and the CLI

| SDK | Form and distribution | Phase |
| --- | --- | --- |
| Rust | `sdk/rust`: `api` types with HTTP and in-process clients | 0 |
| Python | `sdk/python`: pure Python generated from the catalog's JSON Schemas, with PEP 740 attestations [PEP 740] | 1 |
| TypeScript | `sdk/typescript`: pure TypeScript for Node.js, Deno, Bun and browsers, through trusted publishing [npm security plan] | 2 |
| C ABI | `sdk/c`: `libcrucible` for C, C++, C#, Java, Julia, MATLAB and CAD add-ins; archives per Tier 1 target | 2 |

Every index publishes the SDK as `crucible-sdk`, since unrelated projects hold `crucible` on PyPI and crates.io [PyPI crucible][crates.io crucible]. The name is free on crates.io, PyPI and npm [crates.io crucible-sdk][PyPI crucible-sdk][npm crucible-sdk]. ECO reserves it on every index at the phase 0 name gate.

**Decision D-ECO-11:** The official SDKs are Rust, Python, TypeScript and a C ABI. Other languages bind the C ABI or generate a client from the JSON Schemas and OpenAPI 3.1 description. *Why:* these four cover systems code, scripting, web, agents and every foreign-function interface, and each extra SDK multiplies parity testing. *Rejected:* official Java, C# and Julia SDKs. A Python SDK on native extensions, since AGT keeps SDKs pure-language.

SDK versions equal the catalog version. A method is deprecated for at least 12 months before a major removes it, and servers serve the previous major for 24 months.

The C ABI passes canonical JSON through `crucible_call`, streams Evaluations through `crucible_call_stream` and maps CAS objects with `crucible_cas_map`. Handles are opaque, panics never cross it, and removing a symbol needs a new library name (`libcrucible2`).

Every method is `<group>.<name>` in the contract's eight groups (section 7.6). Error codes take the separate form `<family>/<code>` (AGT). ECO asks AGT to add:

| Method | Contract | Failure |
| --- | --- | --- |
| `read.packages`, `read.package` | Search by name, world, licence or badge; one package's manifest, signer, advisories and labels | `package/not_found` with nearest names |
| `compare.resolve` | Manifest plus lockfile → new lockfile and diff, not applied | `package/unsatisfiable` with the PubGrub explanation |
| `edit.grant_capability`, `edit.revoke_capability` | A scoped grant or revocation recorded in `ingot.lock` | `policy/denied` naming the rule |
| `read.events`, `read.subscribe`, `read.unsubscribe` | Events by cursor; webhook subscriptions, by people with `maintainer` or `admin` | `events/cursor_expired`; `events/url_refused` |
| `edit.import_archive` | Repository archive File → design repository, with KLN's integrity rule for imported spans | `archive/incomplete` listing missing objects |
| `read.registry_bundle` | Lockfile → signed offline bundle of its pinned packages | `package/unavailable` |

Publishing, yanking, deprecating and every export are Act classes (AGT).

The `crucible` CLI maps subcommands one-to-one onto methods, with aliases for daily work, and `crucible update parts` lists every substitution a `CatalogSelection` makes. Output is text or canonical JSON (`--json`).

Exit codes are 0 success, 1 Check failures, 2 usage, 3 build error, 4 authorization and 5 infrastructure. `--offline` makes any network need a typed error.

### Events and webhooks

**Decision D-ECO-12:** ECO owns the event envelope, delivery and signing for every tab. Events use CloudEvents 1.0, and webhooks follow Standard Webhooks, signed with Ed25519 (`v1a`) by default. Payloads are thin: ids, opaque references and a link, never design content. KLN's sequence number travels zero-padded in the `sequence` attribute [CloudEvents sequence]. *Why:* both are open specifications with receiver libraries, and asymmetric signatures leave receivers no forging secret. *Rejected:* a custom envelope. HMAC-only signing. Fat payloads, which bypass access control. Per-tab envelopes (round 1). (revised in round 3)

CloudEvents requires `id`, `source`, `specversion` and `type`, with `source` plus `id` unique [CloudEvents]. `source` is the repository, registry or catalog URI, and `type` takes a reverse-DNS prefix from the steward's domain once the name gate fixes it. KLN defines repository, lifecycle and evaluation types, AGT the Act types, and ECO registry types such as `package.yanked`.

1. **Pull.** `read.events` returns events in per-source order, retained at least 30 days (target); CI uses this path.
2. **Push.** Deliveries carry `webhook-id`, `webhook-timestamp` and `webhook-signature`; HMAC-SHA256 (`v1`) serves receivers that cannot verify Ed25519 [Standard Webhooks spec]. Receivers reject timestamps over 5 minutes old.
3. **At least once.** Receivers deduplicate by `webhook-id`, and retries back off with jitter over about three days, then go to a dead-letter queue.
4. **SSRF protection.** An egress proxy checks each resolved address at connect time. It refuses loopback, private, link-local, CGNAT (100.64.0.0/10), IPv6 unique-local and IPv4-mapped ranges unless a self-hosted policy names a host. Every 3xx response counts as a failure [Standard Webhooks spec].
5. **Opaque references.** Above `internal`, payloads carry a per-subscription id, the HMAC of the `ObjectId` under the subscription's key, never an `ObjectId` or file hash.
6. **People only.** Agents receive the same events as MCP resource subscriptions (AGT).

### Exit surfaces

- **Repository archive** (phase 1): a design repository's full history and the CAS objects needed to rebuild it; restoring it reproduces every Change's build hash.
- **Release bundle** (phase 1): a release's neutral Files, the BOM as CSV and JSON, and the signed manifest.
- **Git mirror** (phase 2): Ingot sources, manifests and lockfiles, one Git commit per selected Change.

The archive format and the CAS encoding are open, so a third party can write an independent reader (ECO-O-12). On import, spans keep their integrity only if a device key of a principal in this organization signed the Change (KLN).

**Decision D-ECO-28:** Every ECO surface that moves tenant bytes outside the tenant is an Act in AGT's `release_data` family. That covers archive export, mirror pushes, release bundles, quote requests, connector messages, passports and publishing. At commit each runs one set of checks: labels, screening, a `ControlAuthorization` (KLN) for controlled payloads, and audit. Watermark and expiry join in phase 3. Recurring channels, such as a Git mirror, run under AGT's `standing_release` class (D-AGT-30). Two humans approve it once, fixing recipients, channel, schema, confidentiality ceiling and an expiry of at most 12 months. *Why:* exit paths with different controls leave the weakest open. A standing class controls frequent flows without rubber-stamping. *Rejected:* plain API methods for export (round 1). Controls per exit path, which drift. One Approval per mirror push (round 2). (revised in round 3)

### Enterprise connectors

**Decision D-ECO-30:** ERP, MES and PLM systems connect through the connector worlds of `crucible:connect`. Field mappings are Packages of mapping data, with a table of which system owns each field. A release, change-notice or deviation plan lists deliveries to the organization's own systems as effects under its one Approval (contract section 7.6). Failed deliveries retry until the plan expires. Other messages, such as a new-part request, are separate Acts or a `standing_release`, and inbound data arrives as signed External inputs. *Why:* mappings as data are reviewed like any package, and an approval per ERP message invites rubber-stamping. *Rejected:* a webhook consumer that only reads change notices (round 1). Per-customer integration code. One Act per message (round 2). (revised in round 3)

Outbound records are `ItemMaster`, `BillOfMaterials`, `Routing`, `WorkOrder` and `ChangeNotice`, with routings and work orders mapped by MFG from phase 2. Inbound External inputs carry cost, price, lead time and inventory for MFG's cost models. ERP messages follow OAGi's OAGIS business object documents [OAGi], and MES messages follow B2MML, the XML form of ISA-95 [B2MML].

| Field | Owner by default |
| --- | --- |
| Item number, revision label, lifecycle state | Crucible, or the external PLM under KLN's system-of-record policy |
| EBOM structure, reference designators, effectivity | Crucible (KLN) |
| MBOM, routings and work orders | Crucible (MFG) where it plans manufacturing, else the ERP |
| Cost, price, lead time, inventory | ERP, inbound |
| Stock disposition on change | Crucible decides; the ERP executes |

KLN owns the system-of-record policy (D-KLN-39). Under `External(connector)`, numbers come through the PLM connector, and the release Act publishes into the external item revision.

An external approval is evidence pinned in the release, never an Approval; where the external system is the only approver, the Act is `publish_to_system_of_record` (KLN). Reference connectors for two ERP and three PLM systems arrive in phase 2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| SDKs and C ABI | Generated from one catalog; `crucible-sdk` on every index | AGT's error object in every language | ECO-O-11 | 0 (Rust), 1 (Python), 2 |
| ECO's API methods and CLI | Methods above; aliases, exit codes, offline mode | Typed errors; exit codes 1 to 5 | ECO-O-11 | 1 |
| Events and webhooks | CloudEvents; Standard Webhooks; egress proxy; opaque references | Retries, then dead-letter queue | ECO-O-14 | 1 |
| Repository archive and open encodings | Full history; independent readers | `archive/incomplete` | ECO-O-12 | 1 |
| Outbound Acts | `release_data` checks for every exit path | `label/write_down`; screening failure | ECO-O-28 | 1, 2 (mirror, standing releases), 3 (watermark) |
| ERP and MES connectors | Records out as release effects; External inputs in | `MappingConflict { field, owner }` | ECO-O-27 | 2 |
| PLM subordinate mode | External numbering; external approvals as evidence | `DigestMismatch { expected, found }` | ECO-O-27 | 2 |

## Package registry

The registry distributes every package, from std and translators to solvers, panels and catalog parts. Phase 1 ships a signed first-party index as TUF targets, and the public registry opens in phase 2 (contract section 13.2).

### Names and namespaces

**Decision D-ECO-13:** Every package lives in a namespace that a verified publisher owns, named `namespace::name` as Ingot's `use` writes it. Domain claims own bare names, code-host claims take a prefix (`gh_<org>`, `gl_<org>`), and individuals get `u_<handle>`. *Why:* code-host names are first-come, so a stranger could take the name acme.com needs; Maven Central reuses DNS likewise [Maven Central namespaces]. *Rejected:* a flat namespace, open to squatting. Optional scopes. Unprefixed code-host claims (round 1). (revised in round 2)

| Rule | Detail |
| --- | --- |
| Syntax and spellings | Segments match `[a-z][a-z0-9]*(_[a-z][a-z0-9]*)*`; Ingot `parts::ti::tps62133`, WIT `parts:ti-tps62133`, URL `parts/ti/tps62133`; a WIT collision is refused |
| Reserved | `std`, `crucible`, `core`, `parts`, `standards`, `examples`, `wasi`, `test`, and the prefixes `u_`, `gh_` and `gl_` outside their claims |
| Look-alikes | Names within edit distance 1 of a popular one, or equal after mapping look-alikes, are held for review |
| New versions | ECO's hold: a new version resolves for other organizations after 72 h, except one that fixes a published OSV advisory, which resolves at once with a flag |
| Re-verification and transfer | Domain claims re-verified yearly; transfers by consent or dispute policy, logged |

### Manifest, lockfile and compatibility

A package and a design repository share `ingot.toml` and `ingot.lock`; ING owns the language keys and the module system.

```toml
[package]
name    = "acme::radiation"
version = "1.4.0"
edition = "2027"
license = "Apache-2.0"

[components.view_factors]
world   = "crucible:physics/solver@0.1.0"
context = "evaluation"
fuel    = 2e11                           # must fit the organization ceiling

[components.vendor_sync]
world   = "crucible:connect/connector@0.1.0"
context = "connector"
http    = ["api.acme.example"]           # the only reachable host
secrets = ["acme_api_token"]
```

The lockfile pins each package's version, registry, grants, source and binary hashes and signer identity, plus Assets and External inputs. A changed registry fails resolution, and PubGrub's derivation tree becomes a typed explanation [PubGrub].

At publish the registry refuses incompatible interface changes in minors and patches, as cargo-semver-checks does [cargo-semver-checks]. It records changed outputs and `EntityId`s on test designs, which depend only on source text through `CallSite`.

**Decision D-ECO-14:** A release may change outputs or entity names, but the registry publishes every such change and `crucible update` shows it first. An output-changing patch is labelled, a renaming release is at least a labelled minor, and policy can block both. *Why:* a fix that moves geometry is a design change, and a renamed entity breaks anchors and PMI downstream. *Rejected:* trusting authors' version numbers alone. Forbidding output changes outside majors, which delays fixes. (revised in round 2)

### Publishing and signing

**Decision D-ECO-15:** Publishing never uses long-lived tokens. CI publishes through trusted publishing with a short-lived OIDC credential, or a person publishes with phishing-resistant 2FA, as an audited Act. *Why:* crates.io and npm adopted trusted publishing in July 2025 [crates.io update 2025-07]. After the Shai-Hulud worm spread through maintainer accounts in September 2025, GitHub narrowed npm publishing to these paths [npm security plan]. *Rejected:* long-lived tokens, the main theft target. Publishing without 2FA.

The pipeline runs in order, and a failure at any step returns a typed error with nothing published:

1. Verify the signer against the namespace policy, and the version's novelty.
2. Rebuild where the toolchain allows: first-party packages on the hermetic builder, third-party packages in single-use microVMs.
3. Determinize evaluation Wasm components (D-ECO-8).
4. Run scanners, the export-classification check and the sector rule (D-ECO-29).
5. Run domain acceptance checks contributed as data, such as COV's validity-envelope checks.
6. Measure interface, output and entity-name changes (D-ECO-14).
7. Run test vectors on every engine (ECO-O-6).
8. Sign the index entry and append it to the log.

For a third-party package, steps 2, 3, 5, 6 and 7 run on untrusted-evaluation workers, and their results never enter the global public cache domain. Registry builders and the hermetic builder never run third-party code (contract section 7.8).

[[DIAGRAM diagrams/11-interop-publish-pipeline.jsx: publish pipeline · eight steps, one failure exit, verifying clients]]

Follow the arrows through steps 1 to 8: a failed step exits to the typed error, and clients verify what step 8 signs.

| Layer | Mechanism | Proves |
| --- | --- | --- |
| Author signature | Sigstore keyless signing, logged in Rekor [Sigstore] | Who published these bytes |
| Namespace policy | Trusted publishers signed by the owner's offline key | Who may publish here |
| Namespace delegation | Offline-signed `claimed` role; online-signed `recently-claimed` role for new namespaces | That an online key cannot re-delegate a claimed namespace |
| Build provenance | SLSA provenance, as PyPI's attestations carry [PEP 740][SLSA] | Which source and builder made the bytes |
| Repository metadata | TUF, against rollback, freeze, mix-and-match and malicious mirrors [TUF spec] | Freshness and consistency |
| Transparency | An append-only log that clients verify and organizations may monitor | No split views |

**Decision D-ECO-16:** Every package version carries a Sigstore signature and SLSA provenance. Its signer must match the namespace's trusted-publisher policy, which the owner signs offline. Delegations follow PEP 480, still a Draft [PEP 480]. An offline `claimed` role, re-signed weekly by D-ECO-22's keyholders, holds them, and an online `recently-claimed` role holds new namespaces. Clients warn on first resolution from a recently claimed namespace, and owner-key recovery needs domain re-verification plus a `claimed` re-signing. First-party packages are built at SLSA Build level 3 [SLSA build track] and reproduced bit for bit. *Why:* with online keys alone, TUF cannot protect projects from a compromised registry [PEP 458], which could re-delegate any namespace. *Rejected:* the registry's own record of publishers (round 1). Online-signed delegations (round 2). Signatures without provenance. GPG keys. (revised in round 3)

From phase 2, TUF metadata, checkpoints and provenance are dual-signed, classical plus ML-DSA-87 [FIPS 204], and LMS serves only PLT's software-release signing (contract section 7.8). Air-gapped registries run their own Fulcio and Rekor, or sign with organization keys through `cosign sign --key` [cosign key signing].

### Scanning, advisories and removal

Every publish scans capabilities, signer changes, imports, network targets, secrets, advisories and malware. A malware finding quarantines the version for review within 24 h (target), no code runs at install, and Crucible's own crates carry cargo-vet audits (D-PLT-40).

Advisories use OSV 1.9.1, and ECO registers a `Crucible` ecosystem by pull request in phase 1, the route the schema documents [OSV]. A **correctness advisory** names an operation, translator or package version whose outputs were wrong, as an OSV record with `database_specific.kind = "correctness"`. Lockfiles let `repo` list every released design that used it.

| Act or method | Effect | Who |
| --- | --- | --- |
| Yank | New resolution skips the version; pinned bytes stay downloadable, as in Cargo [cargo yank] | Publisher, as an Act |
| Deprecate | A notice and an optional successor | Publisher, as an Act |
| Quarantine | Download stops; hosts refuse to instantiate; pinned designs fail with `PackageQuarantined` | Operator, with a statement of reasons (D-ECO-35) |
| Legal removal | After a court order or valid notice, and counter-notice where the law provides; a tombstone keeps the hash | Operator, with a statement of reasons |

**Decision D-ECO-17:** Publishers never delete published versions; yanking is their only tool, and leaked credentials go to revocation or an advisory [cargo yank]. *Why:* a released product must rebuild from the same pinned bytes for decades. *Rejected:* a short unpublish window, as npm allows for 72 hours [npm unpublish], which breaks any release pinned inside it. Unrestricted deletion. (revised in round 3)

### Mirrors, licences and the parts catalog

Mirrors are untrusted transport, since clients verify signatures, TUF metadata and log inclusion. Private registries run the same server and deny namespaces off the organization's allowlist, closing dependency confusion. Air-gapped sites import signed bundles, and components are also served in the OCI layout `wkg` reads [wasm-pkg-tools].

Every package declares SPDX expressions for code and data, checked per file in the style of REUSE 3.3 [REUSE 3.3] against organization policy. Each release manifest lists every package, translator and dataset used, so a release ships its software bill of materials.

A `CatalogSelection` is a pure function over pinned definitions, plus pinned offers when it ranks by price (ELX, ING). A `parts::<manufacturer>` namespace belongs to the manufacturer once it verifies, and the operator curates it until then.

**Decision D-ECO-18:** A catalog part's definition is a Package under `parts::<manufacturer>::…`; its offers are signed feeds that a connector turns into dated External inputs. Operator-curated `parts::` Packages hold only facts with datasheet citations and geometry Crucible's generators make from them. Manufacturer CAD files enter only where their terms allow redistribution, recorded in `geometry_licence`, and the registry refuses a missing or non-redistributable data licence. *Why:* definitions must be pinned like code, offers are volatile, and manufacturers often allow design use without redistribution. *Rejected:* hourly price versions in the registry. Definitions outside it. Republishing manufacturer models under Crucible's licence. (revised in round 3)

Migrated KiCad library items stay in private Packages, or go public under CC-BY-SA-4.0 with attribution. KiCad requires redistributed library collections to keep its licence [KiCad library licence].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Signed first-party index | TUF targets from the hermetic builder | Client refuses unverifiable entries | ECO-O-9 | 1 |
| Public registry and trusted publishing | OIDC publishing; the pipeline | Typed error naming the step | ECO-O-9, ECO-O-19 | 2 |
| Namespaces | Prefixes, holds, re-verification, `claimed` roles | `NamespaceTaken`, `HeldForReview` | ECO-O-9 | 2 |
| Resolution and lockfile | PubGrub; signer and registry pinned | `Unsatisfiable`; `SignerChanged` awaits approval | ECO-O-9 | 0 |
| Compatibility labels | Interface, output and entity-name diffs | Refusal naming the item | ECO-O-10 | 1 |
| Signing, policies and transparency | Sigstore, SLSA, offline policies, TUF, log | Client refuses | ECO-O-9 | 1 (first-party), 2 |
| Post-quantum dual signatures | ML-DSA-87 beside the classical algorithm | Single-signed records fail verification | ECO-O-9 | 2 |
| Scanning, advisories, removal | Scans, OSV advisories, yanks, removal with reasons | Quarantine; `PackageRemoved` | ECO-O-19, ECO-O-29 | 2 |
| Private registries and bundles | Deny-by-default namespace map; offline bundles | `NamespaceNotAllowed` | ECO-O-9 | 2 |
| Licence metadata | SPDX, per-file coverage, policy | Invalid expressions refused | ECO-O-31 | 1 |
| Catalog-part definitions | Facts and generated geometry; offers as External inputs | Licence refusal | ECO-O-16, ECO-O-31 | 2 |

## Marketplace

The marketplace is the registry's commercial layer, with no second distribution system. Listings open with the public registry in phase 2, and paid packages in phase 3.

| Publisher level | Requirement | Grants |
| --- | --- | --- |
| Account | Verified email and phishing-resistant 2FA | `u_<handle>` |
| Organization | A domain verified by DNS TXT, or a code-host organization by OIDC (prefixed) | A namespace for it |
| Verified publisher | Know-your-business checks with screening and the sector rule, trader data, a security contact, the publisher agreement | Paid packages; manufacturer-verified catalog parts |
| Certified integration | A passed integration suite | Listing in ordering and quoting flows |

Badges link to the dated record of the checks that ran and never claim quality.

**Decision D-ECO-32:** Verification changes badges, never integrity. All third-party package text reaches readers as `ExternalText`, verified publisher or not, and only first-party documentation from the hermetic builder is trusted. *Why:* verification establishes who published, not that the text is safe to obey; a compromised account would otherwise instruct agents. *Rejected:* trusting verified publishers' text (round 1).

**Decision D-ECO-19:** Paid packages are ordinary registry packages whose download needs a signed, offline-verifiable entitlement, checked before instantiation and never during evaluation. A design that pins a paid version rebuilds with it forever. The steward company is merchant of record: it buys from publishers, invoices buyers and collects VAT and sales tax per jurisdiction. *Why:* evaluation stays offline, and designs never become hostage to billing. EU VAT law treats a platform that authorises the charge or sets the terms as the supplier [EU VAT 1042/2013]. *Rejected:* licence checks inside components. A separate commercial store. Naming publishers as suppliers, which the VAT rule overrides. (revised in round 3)

| Rule | Detail |
| --- | --- |
| Expiry | Blocks new versions and installs only; every paid version stays downloadable for any organization that ever held an entitlement |
| Results | Ordinary CAS objects; a collaborator without an entitlement gets `EntitlementRequired`, never cached, only when an input changes |
| Source | Compiled components with public worlds and test vectors; escrowed source scanned privately |
| Escrow | Source and build recipe with an independent agent; licensees may rebuild if the publisher stops for 12 months; counsel confirms the agreement per jurisdiction first |
| Export and sanctions | A declared `export_classification` (ECCN, EAR99 or not subject, with the basis); screened purchases; the sector rule of D-ECO-29 |
| Pricing and terms | Per seat, organization or usage, metered outside evaluation; the steward's terms govern refunds and disputes |

Suppliers publish one `offer` record (price breaks, stock, lead time, validity) through a connector (D-ECO-18). Manufacturing partners implement `crucible:connect/partner`: quote requests run inside `request_quote` Acts and orders inside `order` Acts. Quotes return as External inputs, and a partner earns "Certified" for 12 months on a published suite.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Verified publishers | Business checks, screening, trader data, dated badges | Verification refused, naming the failed check | ECO-O-29 | 2 |
| Third-party text as `ExternalText` | Every publisher's READMEs, docs, templates and definitions | None; text returned by handle | ECO-O-18 | 2 |
| Paid packages, escrow and scanning | Offline entitlements; merchant of record; escrow; private scans | `EntitlementRequired`, never cached; listing refused on a finding | ECO-O-20, ECO-O-29 | 3 |
| Supplier offers | One `offer` record as dated External inputs | Stale offers flagged in Proposals | ECO-O-16 | 2 |
| Manufacturing partners | Quotes and orders inside Acts; certification suite | `partner-error` mapped to typed errors | ECO-O-28 | 2, 3 (certification) |

## Open-source governance and compliance

### Licence and contributions

**Decision D-ECO-20:** Crucible's code, std, SDKs, WIT packages and translators included, is licensed Apache-2.0 WITH LLVM-exception. Documentation is CC-BY-4.0, and examples are MIT-0. The CAS encoding and archive format carry the steward's Open Web Foundation Final Specification Agreement 1.0, a royalty-free patent promise [OWFa 1.0]. *Why:* the toolchain embeds its code in artifacts users ship, which the LLVM exception covers [LLVM exception]. Apache-2.0's patent licence ends for anyone who sues [Apache-2.0], and it matches Crucible's Rust and Wasm dependencies [wasm-pkg-tools]. *Rejected:* MPL-2.0, whose per-file duties land on every embedder [MPL-2.0][MPL FAQ]. MIT OR Apache-2.0, without a patent grant. An unnamed patent commitment (round 2). (revised in round 3)

Contract section 7.7 fixes dependency licences, and ECO keeps the allowlist that PLT's cargo-deny and ECO-O-31 enforce. Any other licence needs an RFC.

| Dependency licence | Use | Obligation in every distribution |
| --- | --- | --- |
| MIT, MIT-0, Apache-2.0, BSD, 0BSD, ISC, Zlib, BSL-1.0, CC0-1.0, Unicode-3.0, OpenSSL (the pre-3.0 dual licence) | Linked | Notices |
| OFL-1.1, CDLA-Permissive-2.0, CC-BY-4.0, Unicode-3.0 | Bundled data and fonts | Notices with each |
| MPL-2.0 | Linked files | Notices and a source offer per MPL file in every distribution [MPL-2.0]; modifications published under MPL-2.0 |
| OS libraries (glibc, the C++ runtime under its runtime exception, platform frameworks) | Linked dynamically, never shipped | None beyond the platform's |
| LGPL, GPL, AGPL otherwise | Never linked: external tool, External Op or test oracle | Container images ship their source offer |

**Decision D-ECO-36:** std ships no transcribed standards tables; it computes values from the formulas the standards define, such as ISO 286 grades, citing clauses (MEC). Table-only values, such as fastener dimensions, ship in separate `standards::` Packages with a `DataLicence`, licensed from the standards body or supplied by the organization. Counsel reviews the formula approach before phase 1. *Why:* standards bodies hold copyright, and ISO allows its files only "in their original format without any modifications" [ISO 10303 portal]. Substantial extraction can also infringe the EU database right [Directive 96/9/EC]. *Rejected:* tables in Apache-2.0 std, a right Crucible cannot grant. No standards, which leaves `fit(10mm, H7)` unavailable.

**Decision D-ECO-21:** Contributions come under the Developer Certificate of Origin 1.1, with no CLA. Agents never add `Signed-off-by`; agent-assisted commits carry `Assisted-by: <tool, model>`, and a human's sign-off certifies review. Every contribution's added code, declared tool use or not, runs a similarity scan against copyleft corpora, with thresholds per file and per contributor per week. A match blocks the merge until a maintainer clears or rewrites it. *Why:* the DCO certifies knowledge of the work's origin [DCO][LF generative AI], and undeclared or split snippets are what a scan exists for. *Rejected:* a CLA with assignment, which enables relicensing. Provenance trailers alone (round 1). Scanning only agent diffs over 50 lines (round 2). (revised in round 3)

`ChangeProvenance` is mirrored into the public history. Protected paths such as `oracles/` change only through the oracle role and the verifier (contract section 13.2).

### Stewardship and decisions

**Decision D-ECO-22:** The founding company stewards the project until a fixed trigger. It then transfers repositories, trademarks and namespace authority to an existing foundation that already holds trademarks and runs infrastructure. The trigger is the earliest of three events. They are the phase 3 gate, a year with maintainers from three other organizations, and three years after the first stable release. From phase 0 the foundation holds an irrevocable, recorded option on the trademarks with their goodwill; the company keeps quality control until the trigger. A key ceremony gives the TUF root and namespace-policy keys to keyholders, at least half outside the company. *Why:* product data lives for decades, so the kernel must be safe from relicensing or capture. A US mark passes only with its goodwill [15 USC 1060], and one whose owner lets it lose significance is abandoned [15 USC 1127]. *Rejected:* trademark escrow (round 2), with an owner that controls nothing. A new foundation, with no staff. A foundation at launch (contract section 7.7). A charter sentence alone (round 1). (revised in round 3)

The company keeps hosted services, the marketplace, licensed translators, support and certification. Before the transfer the founder decides governance; after it, a steering committee does, with at most one third of seats from one employer.

Significant changes go through public RFCs modelled on Rust's: new operation families, editions, WIT packages, capabilities, registry and licence policy. A shepherd is assigned within 14 days (target), and a ten-day final comment period precedes a written decision. Agents may draft RFCs; only humans approve them.

### Releases, editions and support

PLT owns the release train (D-PLT-27), with a yearly LTS supported for 24 months [Wasmtime releases], and KLN the regulated cloud mode [DFARS 7012]. The registry keeps every version a supported line's designs pin.

ECO assembles the Computer Software Assurance package for medical customers under FDA's guidance [FDA CSA]. It holds risk tiers, oracle evidence, impact notes and a quality agreement template.

**Decision D-ECO-34:** Until the transfer, the company is the CRA manufacturer of every distribution it publishes, open-source releases included. Conformity assessment is done by 11 December 2027 [CRA]. Each stable line states a support period of at least five years. Security fixes reach it by backport or by a free upgrade that raises no OS or hardware minimum, as separate patch releases (`x.y.z`). *Why:* Recital 15 counts monetising through a platform as commercial activity. Article 13(8) sets the five-year floor, and Article 13(10) allows latest-only support through a free upgrade. Annex I Part II(2) asks for separate security updates [CRA]. *Rejected:* manufacturer duties for commercial builds only (round 2). The 24-month LTS as the support period, below the floor.

**Decision D-ECO-23:** Ingot uses per-package editions, as Rust does. Editions interoperate in one build and change only surface syntax, prelude and lints, and `crucible migrate` applies the fixes. An edition never changes a pinned operation's behavior version. *Why:* every edition compiles to one internal form [Rust editions], so a migration is checked by rebuilding. *Rejected:* versioning the language in lockstep, which forces every package to migrate at once. No editions, which freezes early mistakes.

A migration must leave every golden product's and registry test design's output hashes unchanged (ECO-O-13). Editions are named by year, at most one every three years (target), and ING owns the rules within one.

### Security, sanctions and notices

Reports go to `security@`, to `/.well-known/security.txt` with its required Contact and Expires fields [RFC 9116], or to the code host. Acknowledgment comes within 2 business days (target), the 90-day embargo shortens under exploitation, and a bounty starts in phase 2. Ids are OSV and code-host ids until the public registry opens, when the steward applies for CVE numbering-authority scope over its products.

An actively exploited vulnerability gets an early warning within 24 hours and a notification within 72 hours, whatever the embargo [CRA]. These Article 14 duties apply from 11 September 2026. After the transfer the foundation takes Article 24's steward duties.

Correctness defects that could make a product unsafe get the same urgency:

| Severity | Meaning | Response |
| --- | --- | --- |
| C1 | A `SignOff` result is non-conservative, or an export moves manufactured geometry beyond tolerance | Advisory within 72 hours of confirmation (target); affected-release owners notified through `repo` |
| C2 | An `Interactive` result or non-critical export is wrong beyond its bound | Advisory with the next stable release |
| C3 | Metadata or presentation only | Changelog entry |

**Decision D-ECO-29:** The steward classifies each distributable under the EAR and the EU dual-use regime and publishes the statements. Public source with non-standard cryptography is notified to BIS and the NSA [15 CFR 742.15]. The public registry refuses packages whose label has `controls`, and paid packages declare `export_classification`. A sector rule refuses tenants, buyers, support customers and update clients located or established in Russia or Belarus for every commercial artifact and service. Onboarding screens establishment and ownership, and update servers geo-restrict those countries. *Why:* the EU bars industrial design and manufacture software, and its IP licences, for entities established in Russia [EU 833/2014]. The US requires a licence for EAR99 CAD, CAM, PLM and BIM software and updates there [15 CFR 746.8]. *Rejected:* deferring export control (round 1). Restricting only comprehensively sanctioned countries (round 2). (revised in round 3)

Counsel decides once whether public open-source downloads need the authorisation route of Article 5n(9b). The restricted-country list is a dated regulation dataset pinned as an External input, so every change is explicit.

**Decision D-ECO-35:** From its opening, the public registry runs notice and moderation as an online platform. Anyone may file an electronic notice of illegal content, export-controlled and sanctioned content included (DSA Article 16). Every operator yank, quarantine or removal sends the publisher a statement of reasons (Article 17), logged, and publishers may appeal (Article 20). A yearly transparency report is published, and paid listings need trader data (Article 30). A US DMCA agent and repeat-infringer policy apply [17 USC 512][DMCA directory]. *Why:* the registry disseminates publishers' content to the public, and Articles 16 and 17 bind every hosting service [DSA]. *Rejected:* removal on court orders alone (round 2). Relying on the small-enterprise exemptions of Articles 15(2), 19 and 29, which needs a second process later.

Names are a phase 0 gate (contract section 13.1). Flux is renamed, since Siemens sells Simcenter Flux [Simcenter Flux] and flux.ai is a PCB tool [Flux AI].

"Crucible" gets full clearance in classes 9 and 42 in the US, EU, UK, China and Japan. Atlassian still lists Crucible as its mark [Atlassian trademarks], though its product's sales ended in 2025 [Atlassian Crucible]. The brief also covers lapsed products, such as Amazon Game Studios' 2020 game [Crucible game].

The trademark policy allows "works with Crucible" without implying official status. "Crucible-compatible" needs the conformance suite, and modified distributions need another name.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Licence policy | Contract section 7.7's list; source offers; no standards tables in std | A violating distribution is not released | ECO-O-31 | 0 |
| Contribution checks | Human DCO, `Assisted-by`, similarity scan on every contribution | Merge blocked, naming the rule | ECO-O-30 | 0 |
| Binding stewardship | Trigger with backstop; recorded trademark option; key ceremony | Root metadata below the keyholder threshold fails verification | ECO-O-9 | 0 |
| Regulated support artifacts | Pinned versions kept; CSA package per LTS | Line not promoted | ECO-O-22 | 2 |
| CRA manufacturer duties | Five-year support periods; separate security patches; 24 h and 72 h reports | A missed deadline is recorded as an incident | ECO-O-29 | 1 |
| Export classification and sector rule | Statements; registry refusals; sector refusals | `ExportControlled`, `SectorRestricted` | ECO-O-29 | 1 |
| Notices and moderation | Notices, statements of reasons, complaints, DMCA agent | A removal without reasons fails the drill | ECO-O-29 | 2 |
| Name clearance | Names cleared and reserved before freezes | Freeze refused while uncleared | ECO-O-6 | 0 |

## Documentation and community

AGT specifies agent-facing references (D-AGT-23) and UIX the tutorials verified by scripted solutions; ECO specifies the system around them.

**Decision D-ECO-24:** Documentation follows the four Diátaxis types: tutorials, how-to guides, reference and explanation [Diátaxis]. Reference is generated, and every code sample is a tested example. *Why:* each type serves one need, and generated reference cannot drift. *Rejected:* a single manual, which mixes learning and lookup. A wiki, which is untested.

Tutorials follow each golden product from sketch to release. Every code block builds with its Checks passing, every public item has an example and units, and pages ship offline with the desktop app. The registry generates reference docs for every package.

The community has a forum, chat and an issue tracker under the Contributor Covenant 3.0 [Contributor Covenant]. Certification is graded by oracles: practicals with hidden Checks, and hidden test vectors for package developers.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Documentation site | Diátaxis; tested examples; offline copy | A failing example or uncovered item blocks the release | ECO-O-32 | 1 |
| Package reference docs | Generated per version at publish | Missing docs warn; std refuses | ECO-O-32 | 2 |
| Certification | Practicals from a rotating held-out pool | Fail with the failed Checks listed | ECO-O-32 | 2 |

## Migration from incumbent tools

### What can move

| Source data | Moves as | Path | Phase |
| --- | --- | --- | --- |
| Part geometry, assembly structure, properties | `Body` with identity, `Assembly` of Instances, metadata | AP242, Parasolid or licensed readers | 1 (STEP), 2 (licensed) |
| Semantic PMI; mates | GD&T on faces, presentation-only and flagged where the source has no semantics; mates where exposed, else fixed placements | AP242, or a licensed reader as its qualification record states | 2; 3 |
| Drawings; PDM history | PDF and DXF Assets; released revisions without feature history | Files; PLM connectors (D-ECO-30) | 1; 4 |
| NC programs | `Program` Items verified by MFG's `verify_nc`, never converted; macro calls need the machine's macro library (MFG) | Bulk import | 2 |
| Tool libraries, posts, setup sheets | Tool Assemblies through the tool-data readers; posts and sheets as Assets | Bulk import | 2 |
| ECAD designs and libraries | Schematics, boards, symbols, footprints and parameters; library parts become catalog parts (ELX) | Own EAGLE XML reader; KiCad for the rest (D-ECO-31) | 3 |
| Boards without schematics | Layout, netlist and BOM | IPC-2581 and ODB++ read | 3 |

**Decision D-ECO-31:** Proprietary ECAD designs migrate through KiCad's importers in a pinned container, then Crucible's own KiCad reader; EAGLE XML gets its own reader. *Why:* Autodesk ended EAGLE sales and support on 7 June 2026 [EAGLE]. KiCad 9 imports EAGLE, CADSTAR, EasyEDA, Altium, P-CAD and Fabmaster [KiCad 9 docs]. KiCad is GPL-3.0 or later [KiCad licences], so it runs only out of process. *Rejected:* licensed ECAD translators, which mostly do not exist. Own readers for every undocumented format.

**Decision D-ECO-25:** Crucible does not import parametric feature history from proprietary systems. It imports geometry, structure, semantic PMI and metadata, and offers design-intent reconstruction as a reviewed Proposal. *Why:* replaying undocumented features without the original kernel gives different geometry, silently, while reconstruction can be checked. *Rejected:* feature trees through licensed SDKs, fragile per version. Macro-recording replay.

Configurations, design tables, equations and sketches stay behind; their results arrive as geometry.

### Reconstruction and tooling

Reconstruction, run by an agent role and delivered as a Proposal, has four steps:

1. **Recognize** extrusions, holes with `HoleSpec`, fillets, chamfers, patterns, shells and drafts: rules for prismatic parts, learned segmentation for the rest. BRepNet's convolutions over oriented coedges inform the model [BRepNet]. Shipped models train only on Crucible's procedural corpus and licensed data (D-AGT-22).
2. **Generate** Ingot features with std features and the imported PMI as constraints.
3. **Verify** against the import: Hausdorff distance under 1 µm (target), equal topology in normal form, every PMI item re-attached through a `Query`.
4. **Fall back** to imported geometry for regions that fail, joined by direct-edit operations and listed.

The phase 3 target: 9 of 11 NIST parts and 80% of a held-out prismatic set rebuild with all PMI.

| Source or tool | Approach | Phase |
| --- | --- | --- |
| OpenSCAD sources; spreadsheet design tables | Own translator for CSG, extrusions and modules, with OpenSCAD (GPL-2.0 [OpenSCAD COPYING]) only as an external oracle; tables become parameter files and variant sets | 2 |
| Zoo KCL [KCL docs]; CadQuery and build123d, Apache-2.0 on Open CASCADE [CadQuery][build123d] | KCL translated, pipelines to `\|>`; Python sources run in a pinned container whose operation trace becomes Ingot | 3 |
| The organization's own Onshape FeatureScript | Translator for std calls, units and sketches, tested on the licence-filtered ABC subset; unknown calls become `Untranslated` stubs | 4 |
| `crucible import scan` and bulk import | Inventory of formats, broken references and duplicates; resumable | 2 |
| Subordinate mode | The enterprise PLM stays the system of record while Crucible releases into it (D-ECO-30) | 2 |
| Parallel run, round-trip bridge, library migration | Re-import incumbent releases and report differences; standard parts to Packages | 3 |

Translators run in the tool context and must match the original's STEP export within tolerance. Migration never modifies source data, and every converted model keeps its source File by hash.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| MCAD migration | Geometry, structure, PMI, metadata, drawings | Per-file report; nothing dropped silently | ECO-O-1, ECO-O-17 | 1 to 4 per row |
| Manufacturing-data migration | Programs, tool libraries, posts and setup sheets | Unverified programs never reach a transfer Act (MFG) | ECO-O-17 | 2 |
| ECAD migration | EAGLE reader; KiCad as an external tool; legacy board read | `Untranslated { construct }` per file | ECO-O-25 | 3 |
| Reconstruction and source translators | Recognize, generate, verify, fall back | Unverified regions stay imported and are reported | ECO-O-21 | 2 to 4 per row |
| Inventory, bulk import, subordinate mode | Scan, convert, coexist | Per-file report; resumable | ECO-O-17, ECO-O-27 | 2 |

## State of the art

Figures are targets.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| STEP AP242 translation | Schema-generated Part 21 plus CAx-IF practices [CAx-IF GVP][CAx-IF 58J] | Commercial translators in CAx-IF rounds; Open CASCADE 8.0.1 [OCCT releases] | Three-layer Rust translator (D-ECO-3) in every round (D-ECO-5) | Round results; volume and area within 0.05%; zero SFA errors; PMI statistics equal on every NIST case |
| STEP read throughput | Streaming Part 21, lazy resolution | Open CASCADE | Streaming, parallel translation, deterministic merge | A 1 GB file at least 2× Open CASCADE on the reference laptop; browser within 3× of native |
| Proprietary CAD import | Vendor SDK access | CAD Exchanger, HOOPS Exchange, Datakit [CAD Exchanger formats][HOOPS Exchange][Datakit] | Licensed, out of process, without egress, pinned (D-ECO-2) | Qualification on NIST and held-out native models |
| Validation and repair | Validation properties as receiver oracles [CAx-IF GVP] | Open CASCADE Shape Healing [OCCT shape healing] | `anvil::heal` with bounds per entity | Healed entities bounded; re-export within production thresholds |
| Sandboxed extensions | Component Model async in the callback ABI [CM concurrency]; WASI 0.3 [WASI 0.3] | Wasmtime [WASI 0.3]; jco [jco] | Async `crucible:ops` with ordered completions (D-ECO-9); one browser runtime (D-ECO-10) | Every first-party world on Wasmtime, JavaScriptCore, V8 and SpiderMonkey; ≤ 1.6× native Rust in Wasmtime, ≤ 2.5× in browsers |
| Deterministic execution | Injected metering [wasm-instrument][finite-wasm]; Wasm 3.0 deterministic profile [Wasm 3.0] | Wasmtime fuel, native only [Wasmtime determinism] | PLT's determinizer at publish (D-ECO-8) | Identical outputs and traps on 10⁴ vectors per component |
| Supply-chain integrity | Sigstore [Sigstore]; SLSA v1.2 [SLSA]; PEP 740 [PEP 740]; TUF with offline delegations [TUF spec][PEP 458][PEP 480] | PyPI attestations; npm and crates.io trusted publishing [npm security plan][crates.io update 2025-07] | All of these, with offline namespace policies, a `claimed` role and pinned signers (D-ECO-16) | Every entry verifiable offline; no online key adds a publisher or re-delegates a namespace; first-party packages reproduced |
| Resolution and SemVer | PubGrub [PubGrub]; Rustdoc-JSON linting [cargo-semver-checks] | uv, on PubGrub [uv resolver]; Cargo's backtracking resolver [Cargo resolver] | PubGrub with typed explanations; interface, output and name diffs (D-ECO-14) | Full graph under 1 s; seeded breaks all caught, no false refusals |
| Vulnerability data | OSV 1.9.1 [OSV] | OSV.dev, RustSec, GitHub Advisory Database | OSV plus correctness advisories | Advisory-to-lockfile match under 1 h |
| Events and webhooks | CloudEvents 1.0 [CloudEvents]; Standard Webhooks [Standard Webhooks spec] | Svix and the other listed implementations [Standard Webhooks] | Both, Ed25519 by default, behind an egress proxy (D-ECO-12) | Reference verifiers; delivery under fault injection |
| Board exchange and ECAD migration | IDX V6 [prostep IDX]; KiCad importers [KiCad 9 docs] | KiCad 9 [KiCad 9.0] | IDF and IDX readers; KiCad as an external tool (D-ECO-31) | Netlist equality and empty Gerber XOR against the source tool |
| Feature recognition | B-rep message passing [BRepNet]; rules for prismatic parts | BRepNet [BRepNet] | Rules plus segmentation trained on licensed data, verified by rebuild | 9 of 11 NIST parts rebuilt with PMI by the phase 3 gate |
| Documentation | Diátaxis [Diátaxis]; tested reference | rustdoc documentation tests [rustdoc doctests] | Diátaxis, tested and offline (D-ECO-24) | Coverage 100%; every example builds |

Deviations, with reasons:

- Licensed translators run outside evaluation: determinism and portability.
- Wasm components are CPU-only: no deterministic, portable GPU interface exists for sandboxed code.
- No 64-bit memories, and HDF5 formats wrap the C library: maturity.

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Every Tier 1 target | Translators differing per platform | Determinized translators; byte-identical exports (ECO-O-4) |
| Windows, macOS, Linux | Licensed SDKs ship for some OS and architecture pairs only | Run where the vendor ships, else on a server; the External input is the same everywhere |
| Windows ARM64 | Wasmtime Tier 3 [Wasmtime tiers]; licensed SDK builds | Third-party components already out of process (D-ECO-26); ARM64 builds are a vendor criterion, and translators run on a server until one ships |
| Browsers | No native Component Model; no local tool or connector context | One runtime (D-ECO-10); third-party evaluation components remote until the bridge passes; imports upload bytes to CAS first, so Asset hashes match desktop |
| iPadOS (Tier 2) | Guidelines 2.5.2, 3.2.2(i) and 4.7 [App Review] | WKWebView shell; first-party components in the app; registry components remote |
| Android (Tier 2) | Wasmtime Tier 3 [Wasmtime tiers]; Play's downloaded-code rule [Google Play DNA] | No world imports Android APIs; PLT funds upstream coverage |
| Air-gapped installs | No Sigstore, public registry or licence servers | Offline bundles with a private root and `cosign sign --key`; offline activation as a vendor criterion; offline entitlements |
| Text inside files | Encodings and normalization differ | Decode per the declared encoding, normalize names to NFC, keep original bytes |

## Interfaces with other subsystems

| Tab | ECO requires | ECO provides |
| --- | --- | --- |
| ANV | Builders with healing; certified mass properties; D-ANV-31, `import_map`, normal form, `exchange_form`; `crucible:geom` and `anvil::measure_*` | `crucible:ops` bindings from its catalog |
| MEC | GD&T, its AP242 mapping and PMI eligibility; `ShapeAspect`; joints; flat DXF conventions; characteristic balloons; formula-computed standards values; `crucible:product` with KLN | Board readers; AP242 and QIF translators; drawing writers; `standards::` Packages and their licence rule |
| FLX, COV | Field encodings; the FMI and SSP runtime (D-FLX-30); `crucible:field` and `flux::sample`; solver and constitutive semantics; domain acceptance checks | `crucible:ops` bindings; hosting for solver and constitutive components; package metadata for the coverage map; FMU packaging; Field, IFC, GDSII, OASIS, MatML and ISO 10303-235 codecs |
| ELX | Board, netlist and library models; IDX, IPC-2581, ODB++, KiCad, harness and robot semantics; SPICE dialects; `CatalogSelection`; SysML v2 and ReqIF mappings | Board and harness readers and writers; ECAD migration; `parts::` publishing and its licence rule; the offer schema and connectors |
| MFG | Output packages; machine, tool and toolpath models; `verify_nc` and macro libraries; the phase 1 inspection loop; strategy, post, nesting, slicer and recognizer worlds; routing and work-order mapping | Every `io/` writer and its phase; QIF Results and CSV import; tool-data readers; ERP and MES connector worlds; NC migration |
| ING | Module system, manifest keys, editions, `ingot_sdk::Cx`, wrapper conventions, version rules with entity-name changes | Registry and signing; interface diffs (D-ECO-14); determinized components; the RFC process |
| KLN | Leaf inputs; the limit-outcome catalog; `crucible:host`; event types and sequence numbers; `release_data` commit records; the system-of-record policy; `ControlAuthorization`; span integrity on import; the two-person list (D-KLN-41); the regulated cloud mode | Determinized hashes for keys; event delivery; ERP, MES and PLM connectors; the software supply chain; feeds as External inputs; the watermark transform |
| AGT | `std::agents` and `std::explore`; the `<family>/<code>` error form; Act classes, `release_data` and `standing_release` (D-AGT-30); `ExternalText`; render rules for untrusted Bodies; audit; MCP subscriptions | Catalog entries above; registry, event and archive behavior; importers returning `ExternalText`; licence metadata; partner connectors; `release_data` members for every exit path |
| PLT | Determinizer, overhead and call-overhead tables; Wasmtime LTS and 7-day patches; sandbox, egress enforcement and microVM workers; the browser runtime and bridge (PLT-O-WASM-1); `crucible:host/parallel`; LMS release signing; cargo-vet audits; NFC normalization | Worlds to enforce; declared memory limits; component descriptions; font packages; the licence allowlist; export classification, the sector rule and CRA reporting |
| UIX | The `panel` and `canvas2d` worlds; theme, keymap, template and tutorial schemas; rendering of reports, grants and package pages | The registry; package metadata, capability descriptions and badges; licensed translators as external tools |

Outside users get the SDKs, C ABI, CLI, webhooks, and the archive and CAS encoding specifications.

## Oracles

ECO's oracles live in `oracles/eco/`, readable but not writable by agents. Each has a held-out split outside the agent-readable tree (contract section 3, principle 6).

Corpus oracles (1 to 3, 15 to 17, 21, 23 to 26, 32) hold out files by a fixed hash rule. Generated-input oracles (5, 7 to 10, 14, 18 to 20, 28 to 31, 33, 34) draw seeds at CI time. Golden-product oracles (4, 6, 11 to 13, 22, 27) add variants with perturbed parameters.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ECO-O-1 | STEP readers: validation properties against Anvil's values on every corpus file | All within production thresholds; 95% within 0.05% on volume and area (target) |
| ECO-O-2 | Semantic PMI export and import on the NIST CTC, FTC, STC and HTC cases | Every item equal in type, value, tolerance, datums and targets; facet-face controls presentation-only |
| ECO-O-3 | Exported files: generated EXPRESS rules, NIST SFA, XSD and consortium validators | Zero errors |
| ECO-O-4 | Export determinism: every golden product in every format on every Tier 1 platform, and the run build's AP242 and 3MF from the gate release | Byte-identical Files |
| ECO-O-5 | Readers under structure-aware and grammar-based fuzzing | No panic, no allocation beyond limits, termination within fuel; 10⁹ executions per release without a new crash (target) |
| ECO-O-6 | Engine identity: 10⁴ vectors per first-party component on Wasmtime (x86-64, ARM64), JavaScriptCore, V8 and SpiderMonkey, with `crucible:ops` answered in and out of process and out of order; rerun before any engine upgrade | Identical outputs, host-call sequences and trap points |
| ECO-O-7 | Publish-time and build-time determinization with one determinizer version | Byte-identical binaries; forbidden features refused with offsets |
| ECO-O-8 | Isolation: red-team components reaching forbidden imports, undeclared hosts, foreign directories, secrets, labelled reads plus egress, a hard-coded confidential `ObjectId` and worker credentials; a native guest trying DNS, TCP, UDP and HTTP egress; browser-sandbox JavaScript trying `fetch`, WebSocket, `importScripts` and navigation | Every attempt refused, typed and audited; workers hold no tokens, handles or keys |
| ECO-O-9 | Registry integrity: altered bytes, rollback, freeze, mix-and-match, split views, forged provenance, an online key adding a publisher or re-delegating a claimed namespace, an unwarned recently claimed namespace, signer changes, lapsed domains, unlisted namespaces, a root below threshold | Every case detected; rebuilt first-party hashes equal published ones |
| ECO-O-10 | Compatibility gates: seeded breaks, output changes and entity renames in minors and patches | Breaks refused; changes labelled |
| ECO-O-11 | SDKs and C ABI: AGT golden transcripts through every SDK; ABI symbol diff | Byte-identical canonical JSON; no symbol removed in a major |
| ECO-O-12 | Exit: an independent reader in another language, built from the specifications, reads golden-product archives | Same Changes, Body measurements within bounds, same BOM |
| ECO-O-13 | Edition migration on every golden product and registry test design | Identical output hashes |
| ECO-O-14 | Webhooks under outages, failing receivers, duplicates, DNS rebinding, redirects and SSRF probes into private, CGNAT, unique-local and IPv4-mapped ranges | At least once, deduplicated, ordered, signed; probes and 3xx refused; no `ObjectId` in a payload above `internal` |
| ECO-O-15 | Licensed translator qualification per pinned version | Record reproduces; thresholds met or the version flagged |
| ECO-O-16 | Every catalog row on its conformance suite (3MF with and without beam lattices, Reference FMUs, SSP, IFC, KiCad, Gerber re-reading, QIF Results and CSV import, tool data within 1 µm) | Every row at or below the current phase passes |
| ECO-O-17 | Nothing lost: source entities counted by kind against report entries, per corpus and bulk-import file | Every entity accounted for |
| ECO-O-18 | Untrusted content: injections in names, PMI, notes, metadata, READMEs, embossed text and textures (shared with AGT) | No string reaches an identifier or agent context except as `ExternalText`; unendorsed derived Bodies carry `data_untrusted` |
| ECO-O-19 | `crucible add` and `crucible update` traced | No package code runs |
| ECO-O-20 | Paid packages offline with valid, expired and revoked entitlements | Pinned designs always rebuild; unentitled new versions blocked |
| ECO-O-21 | Reconstruction and source translation on NIST parts and a held-out prismatic set | 9 of 11 NIST parts and 80% of the set within 1 µm with all PMI by the phase 3 gate (target) |
| ECO-O-22 | Re-export of archived golden-product releases from every earlier stable and LTS release | Byte-identical to the archived Files |
| ECO-O-23 | Part 21 layer: read then write every corpus file; dictionary-driven against generated access | Every instance reproduced; equal values |
| ECO-O-24 | Round trips in normal form: self round trips and Open CASCADE differential reads | The suites' pass lines; every disagreement triaged |
| ECO-O-25 | Board writers and ECAD migration on open EAGLE, Altium and KiCad designs and Crucible boards | Netlists equal the source tool's; Gerber XOR empty; ODB++ matches KiCad's writer |
| ECO-O-26 | Board exchange: KiCad's IDF and STEP exports of an open board | Outline, holes, keep-outs, heights and reference designators equal the source |
| ECO-O-27 | Connectors against a mock ERP, MES and PLM, replaying every event, with a release whose plan carries ERP and MES effects | Idempotent; field ownership kept; effects delivered under one Approval and retried; external approvals pinned as evidence only |
| ECO-O-28 | Every exit path with and without an approved `release_data` plan, and a standing release given an over-ceiling payload | Nothing leaves without one; label, screening, authorization and ceiling failures refuse the commit |
| ECO-O-29 | Compliance: labelled or unclassified packages, screened parties, buyers and update clients established in Russia or Belarus, escrow scans, an exploited-vulnerability drill, a notice through to its statement of reasons | Refused or flagged; CRA reports drafted within 24 h and 72 h; every removal has a statement of reasons |
| ECO-O-30 | Contributions without a human `Signed-off-by`, with an agent's, without `Assisted-by`, with seeded copyleft snippets, and with a snippet split across small undeclared commits | Every case blocks the merge |
| ECO-O-31 | Licence policy on every distribution and corpus: contract section 7.7's list, notices, source offers, standards tables, `parts::` data licences, corpus evidence | No disallowed licence; every notice and offer present; no corpus item without evidence |
| ECO-O-32 | Documentation and certification | Every example builds; coverage 100%; graders agree with reference solutions |
| ECO-O-33 | Watermarks for several recipients | Each file traces to its release and recipient by recomputation |
| ECO-O-34 | ECO's published WIT packages against their tables | Every listed interface, type and failure present; nothing else in a stable gate |

## Phasing

| Phase | ECO contribution to the gate |
| --- | --- |
| 0 | ECO-O-6 and ECO-O-7 green in the determinism suite; `crucible:` packages at 0.x, ECO's own specified (ECO-O-34); names cleared and `crucible-sdk` reserved on every index; STEP layer 1 from hash-pinned schemas; licence and contribution checks; the stewardship trigger, trademark option and key ceremony; Rust SDK |
| 1 | GP1: AP242 with geometry, structure, validation properties and semantic PMI passing ECO-O-1 to ECO-O-4, in a release bundle; QIF Results and CSV import of external metrology. GP2: 3MF with beam lattices marked required, plus a Core mesh, passing consortium validation and the bureau's file-acceptance test. The gate release reproduces the run build's AP242 and 3MF (ECO-O-4). Also drawings, AP203 and AP214 read, STL, the first-party index, the first CAx-IF round, the Python SDK, CLI, webhooks, archive, docs, export classification and CRA reporting |
| 2 | GP3 and GP4 exchanged with an external CAD system by AP242 round trip with persistent ids; GP3's legacy programs and tool libraries imported; GP4's flat patterns as DXF. Also licensed translators, board exchange, the public registry with notices and moderation, standing releases, connectors, the browser sandbox once the bridge passes, the TypeScript SDK, the C ABI and dual signatures |
| 3 | GP5's board fabricated and assembled from Crucible's Gerber X2, XNC, IPC-2581C or ODB++ and placement outputs; FMI import; ECAD migration; watermarks; paid packages and certified partners |
| 4 | GP6 FE and CFD models exchanged with an external solver; FMU export and SSP (contract section 13.4); robot descriptions; IDX change proposals |
| 5 and later | GP8 round-tripped through IFC 4.3; AP239 and AP233; GP14's IFC export in phase 7 |

## Open questions

1. **Translator vendor.** Kept. The choice among CAD Exchanger, HOOPS Exchange and Datakit depends on terms only negotiation reveals. They cover server use, unlicensed rebuilds, ARM64 builds and offline activation. The founder signs the first agreement before the phase 2 gate.
2. **CAx-IF terms.** Closed: round files enter `oracles/` only where the forum's terms allow, and the fee is a phase 1 budget line.
3. **EXPRESS sources and `espr`.** Closed by D-ECO-33 and the fork of `espr`'s parser.
4. **OSV ecosystem.** Closed: a pull request registers `Crucible` in phase 1, and correctness advisories carry `database_specific.kind = "correctness"`.
5. **Foundation.** Closed by D-ECO-22: an existing foundation with a recorded trademark option.
6. **Marketplace terms.** Closed by D-ECO-19: the steward is merchant of record, and the founder sets the fee level when paid packages open.
7. **ODB++ terms.** Closed: counsel reads the partnership terms before the phase 3 writer starts. If they forbid Apache-2.0, the writer ships as an external tool.
8. **iPadOS.** Closed by contract section 7.4: registry components evaluate remotely.
9. **CVE identifiers.** Closed: OSV and code-host ids, then numbering-authority scope once the public registry opens.
10. **Test corpora.** Closed by D-ECO-37 and contract section 13.3.
11. **Component Model.** Closed: the re-encoding rule covers encoding changes, and 64-bit memories wait for every Tier 1 browser engine.
12. **Findings declined or applied in part.**
    - R4-29, R4-09, R4-10 (round 2): board import and NC and tool-data migration stay in phase 2. Contract section 13.2 limits phase 1 to GP1 and GP2.
    - R5-25 (round 2): no foundation at phase 0 (contract section 7.7); the backstop, trademark option and key ceremony bind the trigger.
    - R11-29: applied, but its premise about the steward's size no longer holds (contract section 13.2); Articles 20 and 30 are adopted by choice.
    - R11-32: the permission request is due "before layer 1's first release" rather than by a calendar month, since milestones are ordered, not dated.
    - R11-49: CNA scope follows the public registry's opening, since the program has no human team (contract section 13.2).
    - R11-45, R11-28, R9-47: applied here; the contract text they touch is CCR-ECO-12, CCR-ECO-10 and CCR-ECO-11.
    - R9-26: ECO keeps a short table of its own four packages beside the index.
    - R8-23, R11-33: ECO applies its part (D-ECO-37); MEC, ANV and AGT own the rest.

## Contract change requests

- CCR-ECO-8 and CCR-ECO-9: accepted in contract v5 (section 7.4).
- **CCR-ECO-10 (R11-28).** Contract section 7.7 adds a CRA support period of at least five years per stable release line. Security fixes reach it by backport or by a free upgrade that raises no OS or hardware minimum, as separate patch releases. *Reason:* the 24-month LTS is below Article 13(8)'s floor (D-ECO-34).
- **CCR-ECO-11 (R9-47).** Contract section 7.6 writes the write-down error as `label/write_down`, the `<family>/<code>` form that keeps errors out of the method namespace.
- **CCR-ECO-12 (R11-45).** Contract section 13.1's phase 0 gate adds "and the SDK name reserved on crates.io, PyPI, npm, Maven Central and NuGet". *Reason:* the bare name is taken on PyPI and crates.io, and names enter lockfiles.

## Sources

Pages opened during research for this tab.

- [ISO 242] ISO 10303-242:2025, edition 4: https://www.iso.org/standard/84300.html
- [ISO 10303 wiki] ISO 10303 overview of application protocols: https://en.wikipedia.org/wiki/ISO_10303
- [CAx-IF GVP] CAx-IF Recommended Practices for Geometric and Assembly Validation Properties, v4.6: https://www.mbx-if.org/documents/rec_prac_gvp_v46.pdf
- [CAx-IF 58J] CAx-IF Round 58J test suite, v1.1: https://www.mbx-if.org/home/wp-content/uploads/2026/08/test_suite_58j_v11.pdf
- [MBx-IF] MBx Interoperability Forum home: https://www.mbx-if.org/home/
- [NIST MBE PMI] NIST MBE PMI validation and conformance testing: https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0
- [OCCT releases] Open CASCADE Technology releases: https://github.com/Open-Cascade-SAS/OCCT/releases
- [espr] espr EXPRESS compiler documentation: https://docs.rs/espr/latest/espr/
- [CAD Exchanger formats] CAD Exchanger supported formats: https://cadexchanger.com/formats/
- [HOOPS Exchange] HOOPS Exchange product page: https://www.techsoft3d.com/products/hoops/exchange/
- [Datakit] Datakit home: https://www.datakit.com/en/
- [ISO 14306] ISO 14306-1:2024, JT: https://committee.iso.org/standard/86063.html?browse=ics
- [3MF specifications] 3MF specifications: https://3mf.io/spec/
- [Khronos glTF ISO] glTF 2.0 as ISO/IEC 12113:2022: https://www.khronos.org/news/press/khronos-gltf-2.0-released-as-an-iso-iec-international-standard
- [AOUSD core 1.0] OpenUSD Core Specification 1.0 release: https://digitalproduction.com/2026/01/05/aousd-releases-openusd-core-specification-1-0/
- [ISO 16739] ISO 16739-1:2024, IFC: https://www.iso.org/standard/84123.html
- [buildingSMART IFC 4.3] IFC 4.3 published as ISO standard: https://www.buildingsmart.org/?p=29521
- [prostep IDX] ECAD/MCAD Collaboration Implementor Forum: https://www.prostep.org/en/projects/ecad/mcad-collaboration-implementor-forum
- [IPC-2581C] IPC-2581 Revision C release: https://www.electronics.org/news-release/ipc-releases-ipc-2581-revision-c-generic-requirements-printed-board-assembly-products
- [ODB++ 8.1] ODB++Design 8.1 update 3: https://odbplusplus.com/blog/design/odbdesign-newest-version-available-and-compatible-with-all-version-8-releases/
- [Gerber wiki] Gerber format: https://en.wikipedia.org/wiki/Gerber_format
- [KiCad formats] KiCad file formats: https://dev-docs.kicad.org/en/file-formats/
- [FMI site] FMI Standard home: https://fmi-standard.org/
- [FMI 3.0.2 news] FMI 2.0.5 and 3.0.2 released: https://fmi-standard.org/news/2024-11-27-fmi-2.0.5-and-3.0.2
- [Modelica newsletter 2026-02] Modelica Association newsletter: https://modelica.org/newsletter/2026-02
- [fmi-ls-wasm] FMI-LS-WASM prototype: https://github.com/modelica/fmi-ls-wasm
- [SSP site] SSP Standard home: https://ssp-standard.org/
- [QIF site] Digital Metrology Standards Consortium: https://qifstandards.org
- [MTConnect 2.5.0] MTConnect Standard Part 1, version 2.5.0: https://docs.mtconnect.org/MBSD_MTConnect_Part_1_2-5-0.pdf
- [OPC 40501-1] OPC UA for Machine Tools: https://reference.opcfoundation.org/MachineTool
- [ReqIF] OMG ReqIF specification page: https://www.omg.org/spec/ReqIF
- [OMG SysML v2] OMG press release on SysML v2, KerML and the Systems Modeling API: https://www.omg.org/news/releases/pr2025/07-21-25.htm
- [WASI 0.3] WASI 0.3 release notes: https://wasi.dev/releases/wasi-p3
- [WASI roadmap] WASI roadmap: https://wasi.dev/roadmap
- [WIT guide] WIT reference in the Component Model book: https://component-model.bytecodealliance.org/design/wit.html
- [WIT gates] Component Model WIT specification, feature gates: https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md
- [Wasm 3.0] Wasm 3.0 announcement: https://webassembly.org/news/2025-09-17-wasm-3.0
- [Wasmtime determinism] Deterministic Wasm execution in Wasmtime: https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html
- [Pulley] Wasmtime Pulley interpreter: https://docs.wasmtime.dev/examples-pulley.html
- [jco] jco: https://github.com/bytecodealliance/jco
- [wasm-instrument] wasm-instrument documentation: https://docs.rs/wasm-instrument/latest/wasm_instrument/
- [finite-wasm] finite-wasm: https://github.com/near/finite-wasm
- [wasm-pkg-tools] wasm-pkg-tools and `wkg`: https://github.com/bytecodealliance/wasm-pkg-tools
- [Sigstore] Sigstore overview: https://docs.sigstore.dev/about/overview/
- [SLSA] SLSA specification v1.2: https://slsa.dev/spec/
- [PEP 740] PEP 740, index support for digital attestations: https://peps.python.org/pep-0740/
- [TUF] The Update Framework: https://theupdateframework.io/
- [crates.io update 2025-07] crates.io development update, July 2025: https://blog.rust-lang.org/2025/07/11/crates-io-development-update-2025-07/
- [npm security plan] GitHub's plan for a more secure npm supply chain: https://github.blog/security/supply-chain-security/our-plan-for-a-more-secure-npm-supply-chain/
- [npm unpublish] npm unpublish policy: https://docs.npmjs.com/policies/unpublish
- [cargo yank] cargo yank: https://doc.rust-lang.org/cargo/commands/cargo-yank.html
- [cargo-semver-checks] cargo-semver-checks: https://github.com/obi1kenobi/cargo-semver-checks
- [PubGrub] PubGrub crate documentation: https://pubgrub-rs.github.io/pubgrub/pubgrub/
- [OSV] OSV schema: https://ossf.github.io/osv-schema/
- [Maven Central namespaces] Maven Central namespace registration: https://central.sonatype.org/register/namespace/
- [CloudEvents] CloudEvents specification: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md
- [CloudEvents sequence] CloudEvents sequence extension: https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/sequence.md
- [Standard Webhooks] Standard Webhooks home: https://www.standardwebhooks.com/
- [Standard Webhooks spec] Standard Webhooks specification: https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md
- [Apache-2.0] Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
- [LLVM exception] SPDX LLVM-exception: https://spdx.org/licenses/LLVM-exception.html
- [MPL FAQ] MPL 2.0 FAQ: https://www.mozilla.org/en-US/MPL/2.0/FAQ/
- [DCO] Developer Certificate of Origin 1.1: https://developercertificate.org/
- [Rust editions] The Rust Edition Guide, what are editions: https://doc.rust-lang.org/edition-guide/editions/index.html
- [Diátaxis] Diátaxis: https://diataxis.fr/
- [ABC] ABC dataset: https://deep-geometry.github.io/abc-dataset/
- [BRepNet] BRepNet, arXiv 2104.00706: https://arxiv.org/abs/2104.00706
- [KCL docs] KCL language documentation: https://zoo.dev/docs/kcl-lang
- [Atlassian Crucible] Atlassian Crucible product page: https://www.atlassian.com/software/crucible
- [Flux AI] Flux home page: https://www.flux.ai/
- [espr crates.io] crates.io API record for `espr`: https://crates.io/api/v1/crates/espr
- [Wasmtime GHSA-394w] Wasmtime advisory GHSA-394w-hwhg-8vgm, out-of-bounds write or crash when transcoding component model strings: https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-394w-hwhg-8vgm
- [Wasmtime GHSA-6wgr] Wasmtime advisory GHSA-6wgr-89rj-399p, data leakage between pooling allocator instances: https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-6wgr-89rj-399p
- [Wasmtime releases] Wasmtime release process and LTS support: https://docs.wasmtime.dev/stability-release.html
- [Wasmtime tiers] Wasmtime platform support tiers: https://docs.wasmtime.dev/stability-tiers.html
- [PEP 458] PEP 458, secure PyPI downloads with signed repository metadata: https://peps.python.org/pep-0458/
- [TUF spec] The Update Framework specification: https://theupdateframework.github.io/specification/latest/
- [FIPS 204] FIPS 204, Module-Lattice-Based Digital Signature Standard: https://csrc.nist.gov/pubs/fips/204/final
- [15 CFR 742.15] 15 CFR 742.15, encryption items: https://www.law.cornell.edu/cfr/text/15/742.15
- [CRA] Regulation (EU) 2024/2847, the Cyber Resilience Act: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402847
- [DFARS 7012] DFARS 252.204-7012, safeguarding covered defense information and cyber incident reporting: https://www.acquisition.gov/dfars/252.204-7012-safeguarding-covered-defense-information-and-cyber-incident-reporting.
- [FDA CSA] FDA, Computer Software Assurance for Production and Quality Management System Software: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-management-system-software
- [LF generative AI] Linux Foundation policy on generative AI contributions: https://www.linuxfoundation.org/legal/generative-ai
- [MPL-2.0] Mozilla Public License 2.0: https://www.mozilla.org/en-US/MPL/2.0/
- [Simcenter Flux] Siemens Simcenter Flux product page: https://www.siemens.com/en-us/products/simcenter/electromagnetics-simulation/flux/
- [Atlassian trademarks] Atlassian trademark list: https://www.atlassian.com/legal/trademark
- [App Review] Apple App Review Guidelines: https://developer.apple.com/app-store/review/guidelines/
- [Google Play DNA] Google Play Device and Network Abuse policy: https://support.google.com/googleplay/android-developer/answer/9888379?hl=en
- [Ucamco Gerber] Ucamco Gerber format downloads: https://www.ucamco.com/en/gerber/downloads
- [KiCad 9.0] KiCad 9.0.0 release announcement: https://www.kicad.org/blog/2025/02/Version-9.0.0-Released/
- [KiCad 9 docs] KiCad 9 documentation, importing non-KiCad projects: https://docs.kicad.org/9.0/en/kicad/kicad.html
- [KiCad 9 PCB editor] KiCad 9 PCB editor documentation: https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html
- [KiCad licences] KiCad licences: https://www.kicad.org/about/licenses/
- [EAGLE] EAGLE (program), citing Autodesk's announcement of the end of sales and support: https://en.wikipedia.org/wiki/EAGLE_(program)
- [OPC 40501-1 v1.02] OPC UA for Machine Tools, Part 1, release 1.02.0: https://reference.opcfoundation.org/MachineTool/v102/docs/
- [Fusion 360 Gallery licence] Fusion 360 Gallery Dataset licence: https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md
- [ISO 10303 portal] ISO standards portal for ISO 10303, notice on electronic inserts: https://standards.iso.org/iso/10303/
- [OCCT licence] Open CASCADE Technology licensing: https://occt3d.com/open-cascade-technology/index.html
- [OCCT shape healing] Open CASCADE Shape Healing user guide: https://occt3d.com/dev/doc/overview/html/occt_user_guides__shape_healing.html
- [OpenUSD up axis] OpenUSD, stage up axis: https://openusd.org/release/api/group___usd_geom_up_axis__group.html
- [IGES wiki] IGES: https://en.wikipedia.org/wiki/IGES
- [SVG 1.1] Scalable Vector Graphics 1.1, Second Edition: https://www.w3.org/TR/SVG11/
- [PDF/A wiki] PDF/A and the parts of ISO 19005: https://en.wikipedia.org/wiki/PDF/A
- [AMF wiki] Additive manufacturing file format: https://en.wikipedia.org/wiki/Additive_manufacturing_file_format
- [lib3mf] lib3mf repository and licence: https://github.com/3MFConsortium/lib3mf
- [3MF beam lattice] 3MF Beam Lattice Extension 1.2.0: https://github.com/3MFConsortium/spec_beamlattice/blob/master/3MF%20Beam%20Lattice%20Extension.md
- [3MF core] 3MF Core Specification: https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md
- [EDIF wiki] EDIF: https://en.wikipedia.org/wiki/EDIF
- [CGNS releases] CGNS releases: https://github.com/CGNS/CGNS/releases
- [SEACAS] SEACAS and the Exodus library: https://github.com/sandialabs/seacas
- [VTKHDF] VTKHDF file format: https://docs.vtk.org/en/latest/vtk_file_formats/vtkhdf_file_format/index.html
- [OpenFOAM v2606] OpenFOAM news, v2606: https://www.openfoam.com/news/main-news
- [OpenFOAM 14] OpenFOAM Foundation downloads, OpenFOAM 14: https://openfoam.org/download/
- [HDF5 track times] HDF5 object creation properties, `H5Pset_obj_track_times`: https://support.hdfgroup.org/documentation/hdf5/latest/group___o_c_p_l.html
- [SDFormat] SDFormat specification: http://sdformat.org/spec
- [Onshape terms] Onshape terms of use, section 1(g)(ii): https://www.onshape.com/en/legal/terms-of-use
- [Component Model] WebAssembly Component Model repository: https://github.com/WebAssembly/component-model
- [CM concurrency] Component Model concurrency explainer: https://github.com/WebAssembly/component-model/blob/main/design/mvp/Concurrency.md
- [MDN default-src] MDN, CSP `default-src`: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/default-src
- [MDN connect-src] MDN, CSP `connect-src`: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src
- [MDN script-src] MDN, CSP `script-src` and `'wasm-unsafe-eval'`: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src
- [PyPI crucible] PyPI record for `crucible`: https://pypi.org/pypi/crucible/json
- [crates.io crucible] crates.io record for `crucible`: https://crates.io/api/v1/crates/crucible
- [crates.io crucible-sdk] crates.io lookup for `crucible-sdk` (not found): https://crates.io/api/v1/crates/crucible-sdk
- [PyPI crucible-sdk] PyPI lookup for `crucible-sdk` (not found): https://pypi.org/pypi/crucible-sdk/json
- [npm crucible-sdk] npm lookup for `crucible-sdk` (not found): https://registry.npmjs.org/crucible-sdk
- [OAGi] Open Applications Group, OAGIS: https://oagi.org/
- [B2MML] MESA B2MML, the XML implementation of ISA-95: https://github.com/MESAInternational/B2MML-BatchML
- [PEP 480] PEP 480, surviving a compromise of PyPI: https://peps.python.org/pep-0480/
- [SLSA build track] SLSA v1.2 build track basics: https://slsa.dev/spec/v1.2/build-track-basics
- [cosign key signing] Sigstore, signing with a key pair: https://docs.sigstore.dev/cosign/signing/signing_with_containers/
- [REUSE 3.3] REUSE Specification 3.3: https://reuse.software/spec-3.3/
- [KiCad library licence] KiCad library licence: https://www.kicad.org/libraries/license/
- [EU VAT 1042/2013] Implementing Regulation (EU) 1042/2013, Article 9a of Regulation 282/2011: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013R1042
- [OWFa 1.0] Open Web Foundation Final Specification Agreement 1.0: https://www.openwebfoundation.org/the-agreements/the-owf-1-0-agreements-granted-claims/owfa-1-0
- [Directive 96/9/EC] Directive 96/9/EC on the legal protection of databases: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:31996L0009
- [15 USC 1060] 15 U.S.C. 1060, assignment of marks: https://www.law.cornell.edu/uscode/text/15/1060
- [15 USC 1127] 15 U.S.C. 1127, definitions, abandonment: https://www.law.cornell.edu/uscode/text/15/1127
- [RFC 9116] RFC 9116, security.txt: https://www.rfc-editor.org/rfc/rfc9116
- [EU 833/2014] Regulation (EU) 833/2014, consolidated text of 20 July 2025, Article 5n: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02014R0833-20250720
- [15 CFR 746.8] 15 CFR 746.8, sanctions against Russia and Belarus: https://www.law.cornell.edu/cfr/text/15/746.8
- [17 USC 512] 17 U.S.C. 512, designated agent and repeat infringers: https://www.law.cornell.edu/uscode/text/17/512
- [DMCA directory] US Copyright Office, DMCA designated agent directory: https://www.copyright.gov/dmca-directory/
- [DSA] Regulation (EU) 2022/2065, the Digital Services Act: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R2065
- [Crucible game] Crucible (video game): https://en.wikipedia.org/wiki/Crucible_(video_game)
- [Contributor Covenant] Contributor Covenant: https://www.contributor-covenant.org/
- [OpenSCAD COPYING] OpenSCAD licence file: https://raw.githubusercontent.com/openscad/openscad/master/COPYING
- [CadQuery] CadQuery repository: https://github.com/CadQuery/cadquery
- [build123d] build123d repository: https://github.com/gumyr/build123d
- [uv resolver] uv resolver internals: https://docs.astral.sh/uv/reference/internals/resolver/
- [Cargo resolver] Cargo dependency resolution: https://doc.rust-lang.org/cargo/reference/resolver.html
- [rustdoc doctests] rustdoc documentation tests: https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html
