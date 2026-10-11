# Interop and ecosystem (ECO)

Crucible reads and writes the open standards of every engineering domain through deterministic translators, and reaches proprietary formats only through licensed translators whose output is pinned. Everything anyone adds, the core team included, ships through one signed registry and behaves identically on every platform. Open formats, an open-source core and binding neutral stewardship keep every design and extension portable.

## Scope and translation architecture

ECO owns five things:

1. **Translation.** The `io/` translators, the translation framework, the standards catalog and translator quality.
2. **The Wasm component contract.** Worlds, contexts, capabilities, sandbox limits and versioning; PLT owns the determinizer and the runtime (contract section 7.4).
3. **Distribution.** The package registry, catalog-part publishing and the marketplace.
4. **Surfaces around `api`.** SDK packaging, the C ABI, the CLI's shape, events, webhooks and enterprise connectors; AGT owns the method catalog.
5. **Stewardship.** Licensing, governance, security disclosure, export classification, trademarks, documentation, certification and migration.

Domain meaning belongs elsewhere: MEC owns tolerancing, ELX the board model, MFG toolpaths and the factory handoff, FLX the FMI runtime, KLN lifecycle records. ECO supplies the machinery, decides which formats exist at what exchange level, and runs the oracles that prove each translator.

| Term | Meaning |
| --- | --- |
| Translator | A reader or writer for one format family: a Wasm component for open formats, an external tool for licensed ones |
| External tool | A native program run out of process in PLT's process sandbox; its output enters builds only as External inputs |
| File | A plain value: name, media type and the SHA-256 of bytes in CAS |
| Exchange level | What a format preserves (visual, geometry, structure, semantics or identity), declared per format and direction |

Three rules run through the tab:

1. The network never reaches evaluation; External inputs do.
2. Nothing is lost silently.
3. Every byte that leaves a tenant leaves through an Act (D-ECO-28).

### Import is a feature

**Decision D-ECO-1:** An import is an Ingot expression over an Asset, evaluated by Kiln like any other feature. No imported state exists outside the program. *Why:* Principle 2 forbids GUI-only state; re-importing a supplier's revision D becomes a one-line change with a reviewable geometry diff; Queries over imported entities re-resolve through provenance like native ones. *Rejected:* one-shot conversion into a native copy, which loses the link to the source and blocks re-import; a separate database of imported objects, which is a second model.

```
use std::io::{read, step}

pub feature motor_mount() -> Assembly {
    let vendor = read("assets/motor_ec45_rev_d.stp", step::options(pmi: semantic))
    vendor.assembly
        .require(vendor.report.lost.is_empty())
        .require(vendor.report.max_deviation < 1um)
}
```

`read` returns `Imported { assembly, parts, bodies, report, source }`, a plain record of core types, where `source` holds the file header. Kiln caches the parse under the Asset's hash, the options and the translator version. The statement's `OpSite` comes from source text (contract section 5), so imported names survive a Git round trip.

### Where translators run

| Source | Mechanism | Context | Enters a build |
| --- | --- | --- | --- |
| Open formats | A Wasm component implementing the `importer` or `exporter` world | Evaluation | As a cached Op output |
| Licensed formats (native CAD, Parasolid, ACIS; JT at first) | An external tool on the vendor SDK, writing the open CAS encoding through the open-source encoder crate | Tool | As an External input in `ingot.lock` |
| Live sources (machines, offers, enterprise systems) | A connector Wasm component | Connector | As an External input in `ingot.lock` |

**Decision D-ECO-2:** Licensed translators never run inside evaluation. They run as external tools, and their output enters builds only as External inputs, content-addressed in CAS and pinned in the lockfile. *Why:* vendor SDKs are native, closed and not bit-reproducible across platforms or releases; pinning their output keeps every build deterministic and lets anyone rebuild the design without the licence. *Rejected:* calling vendor SDKs during evaluation (breaks determinism and cannot run in the browser); compiling vendor SDKs to Wasm (no vendor offers this under its published terms [unverified], and closed code cannot be audited for determinism).

The CAS encoding of `Body`, `Part`, `Assembly`, `Field`, `Material`, PMI and `HistoryRecord`s is an open specification. A tool anyone can re-run, such as an open-source solver in a pinned container, is an External Op instead (contract section 2). The tool manifest says which applies.

A build that lacks a needed External input fails with `ExternalInputMissing { asset, translator, options }`. The fix, `crucible import assets/gearbox.CATProduct` or one click, runs the tool and records the result in a Proposal. A translator upgrade does the same and shows the geometry overlay.

[[DIAGRAM: Translation flow. Sources on the left: open-format Asset, licensed-format Asset, live source. Middle: importer Wasm component (evaluation), external tool on the vendor SDK (tool context), connector Wasm component (connector context); the last two write "External input in CAS, pinned in ingot.lock". Right: the Kiln Op `read(...)` takes the importer and the External input and outputs Imported plus TranslationReport. A dashed line marks the tool and connector contexts as never running at evaluation time.]]

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

Formats that declare units convert to SI with the factor recorded. STL, OBJ and PLY require `units:`, and omitting it is the compile error `MissingUnits`, whose fix lists the bounding box in millimetres, inches and metres. Axis conventions (glTF is Y-up; OpenUSD declares its up axis [unverified]) become an explicit, recorded transform.

Anvil owns imported identity (D-ANV-31). Its discriminator is the source's persistent id (AP242 persistent id, IFC GlobalId, translator native id), else an exact geometric and adjacency signature, never an ordinal. When a supplier sends revision D, `anvil::match_bodies` aligns it with revision C and writes a reviewed `import_map`.

Exports pass through `anvil::exchange_form`. It writes seam edges and pole vertices per receiver profile, approximates procedural geometry by B-splines within a stored bound, and maps every new entity to its `EntityId`. Writers derive AP242 persistent ids from that map, so a partner's returned file maps back to Anvil entities.

The AP242 writer decides semantic PMI per target face. A control whose targets include a facet face exports as presentation only, with a report entry, because the CAx-IF PMI practice reserves semantic PMI for exact geometry [unverified: practice version].

### Deterministic export

Writers run in the evaluation context, so an export is a cached Op. Three rules make the bytes stable:

1. Header timestamps, such as STEP's `FILE_NAME` time stamp, come from the time `repo` recorded for the Change.
2. Instance identifiers, such as STEP `#n` numbers, follow the canonical order of `EntityId`s.
3. Floating-point values use the shortest decimal text that reads back to the same binary value.

A release manifest lists exported Files with their SHA-256, and the signed release tag covers it.

Per-recipient watermarking is a deterministic writer transform, `watermark(file, recipient, parameters)`. KLN's data-package record stores the release file hash, recipient, parameters and recipient file hash. `crucible verify-watermark` recomputes the transform, so any recipient's file traces to its release.

### Untrusted content in imported files

1. **Hostile bytes.** Parsers run with fuel, memory and output limits, and every reader is fuzzed continuously.
2. **Hostile text.** Names, notes, PMI text and metadata come back as `ExternalText` with origin (AGT), and entities get neutral identifiers such as `part_017`.
3. **Hostile appearance.** Readers attach the Asset's `data_untrusted` integrity label to every output, and Kiln joins it into everything derived. Textures are images and geometry can depict text, so a render of such a Body is instruction-capable; AGT decides how agents view it.

Archives (3MF, USDZ, FMU, SSP) are read with limits on entry count, expanded size and compression ratio; a path outside the root fails with `ImportError::UnsafeArchivePath`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `read(path, options) -> Imported` | Pinned Asset to core types, report and header | `ImportError` (unreadable, unsupported schema, missing units, missing External input) with a fix | ECO-O-1, ECO-O-17 | 1 |
| `write(model, format, options) -> File` | `Body`, `Part`, `Assembly` or `Field` to a File in CAS | `ExportError` listing what cannot be carried | ECO-O-3, ECO-O-4 | 1 |
| `probe(path) -> FormatInfo` | Format, schema and edition from the first 4 KiB | `Unknown` with the closest matches | ECO-O-16 | 1 |
| Licensed translation | External tool; output recorded as an External input by Proposal | `ExternalInputMissing` with the import fix | ECO-O-15 | 2 |
| Translation report | Every source entity accounted for | A missing entry blocks the reader's release | ECO-O-17 | 1 |
| Units and axes | Recorded conversion; `units:` for unitless formats | `MissingUnits` with plausible readings | ECO-O-16 | 1 |
| Imported identity and matching | D-ANV-31 discriminators; reviewed `import_map` | `NoCorrespondence { faces }` (ANV) | ANV-O-NAME-4 | 1 (ids), 2 (matching) |
| Exchange form | Seams, poles, B-spline approximations, id map | `NotRepresentable { faces }` (ANV) | ANV-O-NF-1, ECO-O-24 | 1 |
| Deterministic export | Byte-identical Files on every platform | None at run time | ECO-O-4 | 1 |
| Recipient watermarking | Recorded, recomputable transform | `WatermarkUnsupported { format }`; metadata fingerprint only | ECO-O-33 | 3 |
| Untrusted content | Limits, `ExternalText`, integrity labels, archive limits | `ImportError::LimitExceeded`, `UnsafeArchivePath` | ECO-O-5, ECO-O-18 | 1 |

## Standards catalog

### Strategy and exchange levels

Every format gets one strategy:

- **Build:** a Rust Wasm component, generated from a schema where one exists (EXPRESS for STEP and IFC, XSD for XML).
- **Wrap:** a mature open library under a compatible licence, compiled to a Wasm component.
- **License:** a commercial SDK as an external tool (D-ECO-2).

**Decision D-ECO-3:** Open formats are built in Rust as Wasm components and run in the evaluation context on every platform. Each STEP and IFC translator has three layers with separate estimates and oracles: (1) a Part 21 reader and writer with entity types generated from EXPRESS, using late-bound, dictionary-driven access for the long tail of AP242 entities to bound code size; (2) generated checkers for EXPRESS WHERE and uniqueness rules; (3) hand-written mapping modules per application protocol and per CAx-IF recommended practice (geometry and topology, structure, PMI, validation properties, persistent ids), each with its own conformance cases. Layer 3 is the phase 1 critical path. *Why:* the browser and every desktop run the same translator bit for bit, and Anvil, not a second kernel, interprets the geometry; most of a STEP translator is the mapping and the recommended practices, which EXPRESS does not encode. *Rejected:* wrapping Open CASCADE's translator (LGPL-2.1 [unverified], a second kernel's interpretation), which serves as a differential oracle instead; per-platform native libraries (break browser parity); early-bound types for all of AP242 (bloat the Wasm component). (revised in round 2)

`espr`, an Apache-2.0 EXPRESS compiler for Rust, has had no release since 0.4.0 on 20 September 2024, its fifth version [espr crates.io][espr]. Phase 0 evaluates it for layer 1 and plans to own the generator if it stays unmaintained (open question 3).

| Exchange level | Preserved | Example |
| --- | --- | --- |
| Visual | Tessellation, appearance, names | glTF export, OBJ |
| Geometry | Exact B-rep, or a mesh with a stated `ErrorBound` | IGES read, STL |
| Structure | Assemblies, Instances, placements, Part identity, properties, materials by name | AP214 read |
| Semantics | Semantic PMI, kinematics, composites, FE models, connectivity, toolpaths | AP242 with PMI, IPC-2581, QIF |
| Identity | Persistent ids that survive a round trip | AP242 persistent ids, IFC GlobalIds |

Levels are cumulative, and versions below were checked in October 2026. "Owner" is the tab that defines the data's meaning; ECO owns the parser, writer, report and oracles.

Every row shares one contract (`read`, `write` and `probe` at its level) and the report's failure rules. Its oracles are its conformance suite in ECO-O-16 plus ECO-O-1 to ECO-O-5 and ECO-O-17 where they apply.

### Mechanical CAD and product data

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| STEP AP242, Part 21 | ISO 10303-242:2025, edition 4; next edition at committee draft [ISO 242] | R/W | Identity | Build | 1: geometry, structure, validation properties, PMI write. 2: PMI read, persistent ids, tessellation. 3: composites, kinematics | ANV, MEC |
| AP242 edition 5 schema; domain model XML | Used in CAx-IF round 58J for threads and for assembly and kinematics data [CAx-IF 58J] | R/W | Semantics; structure | Build | 3 | MEC; KLN |
| STEP AP203, AP214 | Edition 2; edition 3 [CAx-IF GVP] | R; W | Structure | Build | 1 (R), 2 (W) | ANV |
| STEP AP209 | Extension of AP242 [ISO 10303 wiki] | R/W | Semantics: FE models, results as Fields | Build | 4 | FLX |
| STEP AP238 and ISO 14649 | [unverified edition] | R/W | Semantics: workingsteps | Build | 3 | MFG |
| STEP AP239; AP233 | [unverified editions] | R/W; R | Structure | Build | 5 | KLN; ELX |
| IGES | 5.3 [unverified] | R/W | Geometry | Build | 2 | ANV |
| JT | ISO 14306-1:2024 [ISO 14306] | R/W | Structure, B-rep and PMI where present | License (CAD Exchanger, HOOPS Exchange [CAD Exchanger formats][HOOPS Exchange]), then own reader | 2 (License), 4 (Build) | ANV |
| Parasolid; ACIS | Vendor formats | R/W | Structure, exact geometry | License | 2 | ANV |
| CATIA V5 and 3D XML; NX; Creo; SOLIDWORKS; Inventor | Per translator | R | Structure, PMI where supported | License | 2 | ANV, MEC |
| Solid Edge; Rhino | Per translator | R (Rhino R/W) | Structure | License | 3 | ANV |
| DXF; DWG | [unverified]; vendor format | R/W | Geometry, 2D | Build (DXF); License (DWG) | 2; 3 | MEC |

Crucible never writes native proprietary CAD formats. Exchange back uses AP242 with semantic PMI and persistent ids, tested by the CAx-IF for "ping-pong" iteration [CAx-IF 58J], or licensed Parasolid and JT.

### Mesh, additive manufacturing, scans and buildings

A point cloud is a `Mesh` Body with vertices and no faces, with attributes as Fields.

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| STL | Binary and ASCII | R/W | Geometry; `units:` on read | Build | 1 | ANV |
| OBJ with MTL; PLY | Informal | R/W | Visual; geometry with vertex Fields | Build | 2 | UIX; ANV |
| 3MF | ISO/IEC 25422:2025. Core 1.4.0, Production 1.1.2, Materials 1.2.1, Beam Lattice 1.2.0, Boolean 1.1.1, Secure Content 1.0.2, Volumetric 0.8.0, Toolpath 1.0.0 [3MF specifications] | R/W | Semantics for additive manufacturing | Build; lib3mf as an external oracle [licence unverified] | 1 (Core, Production, Materials, Beam Lattice), 2 (Toolpath), 3 (others) | MFG |
| AMF | ISO/ASTM 52915 [unverified edition] | R/W | Geometry, materials | Build | 2 | MFG |
| glTF 2.0 | ISO/IEC 12113:2022 [Khronos glTF ISO] | W; R | Visual, structure | Build | 2 | UIX |
| OpenUSD | Core Specification 1.0 [AOUSD core 1.0] | R/W | Structure, visual | Build; Pixar's OpenUSD as oracle | 3 | UIX |
| E57; LAS and LAZ | ASTM E2807; LAS 1.4 [unverified revisions] | R/W | Scans, poses, classification | Build | 3 | MEC |
| IFC | IFC 4.3, ISO 16739-1:2024 [ISO 16739][buildingSMART IFC 4.3] | R/W | Semantics for members, plates, openings, property sets | Build on the STEP layers | 5 | MEC |

### Electronics

ELX owns the board model, MFG the factory handoff (package choice, panelization, DFM and DFA, test), and ECO the `io/` readers and writers.

| Format | Version | R/W | Level | Strategy | Phase |
| --- | --- | --- | --- | --- | --- |
| IDF; STEP boards from ECAD tools | IDF version [unverified], exported by KiCad 9 [KiCad 9 PCB editor]; AP242 or AP214 | R | Outline, holes, keep-outs, outlines and heights of placed parts, mapped to Instances with reference designators | Build | 2, on an early 1.x train |
| IDX | V6.0, December 2025; V7 planned [prostep IDX] | R/W, incremental | Identity | Build | 2 (baseline import), 4 (change proposals, export) |
| IPC-2581 | Revision C [IPC-2581C] | R/W | Semantics: stackup, netlist, BOM | Build | 3 |
| ODB++ | ODB++Design 8.1 update 3 [ODB++ 8.1] | R/W | As IPC-2581 | Build; KiCad's writer [KiCad 9.0] as a differential oracle, never linked | 3 |
| Gerber X2 and X3, job file, XNC | Gerber 2026.05 of 19 May 2026; job 2020.08; XNC 2021.11 [Ucamco Gerber] | W; R to verify | Copper, mask, attributes, assembly data | Build | 3 |
| KiCad files | S-expression formats [KiCad formats] | R; W of libraries | Semantics | Build | 3 |
| EDIF; IPC-D-356; Specctra DSN and SES; placements | EDIF 2 0 0 [unverified]; others per ELX | W (SES R) | Connectivity, test, routing, placement | Build | 3 |
| Touchstone, IBIS; VEC | 2.1 and 8.0; VEC 2.2.0, per ELX | R/W | Catalog-part models; harnesses | Build | 3; 4 |

Proprietary ECAD designs migrate through KiCad's importers (D-ECO-31).

### Simulation and analysis

FLX owns the FMI and SSP runtime (D-FLX-30), and ECO owns FMU packaging, FMI-LS-WASM included; phases follow contract section 13.4.

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| FMI | 3.0.2 [FMI 3.0.2 news], with 3.0.3 announced [Modelica newsletter 2026-02]; 2.0.5 for legacy import [FMI site] | R/W | Semantics | Build (FLX runtime) | 3 (import), 4 (export) | FLX |
| FMI layered standards | LS-XCP 1.0.0, LS-BUS 1.3.0-beta.1, LS-STRUCT 1.0.0-rc.1, LS-REF 1.0.0-beta.1, LS-DAE 1.0.0-alpha.1 [FMI site] | R; LS-BUS W | Kept and reported when unsupported | Build | 4 | FLX, ELX |
| FMI-LS-WASM | Non-normative prototype mapping the FMI C API to WIT [fmi-ls-wasm] | R/W, gated | FMUs that run everywhere | Build; ECO joins the working group | 3 (R), 4 (W) | FLX |
| SSP | 2.0.1 [SSP site] | R/W | Structure | Build | 4 | FLX |
| CGNS; Exodus II | [unverified versions] | R/W | Meshes and solutions as Fields | Wrap (D-ECO-4) | 4 | FLX |
| VTK, VTKHDF | [unverified] | W; R | Fields on meshes | Build | 2 | FLX |
| Nastran BDF; Abaqus input | [unverified dialects] | R/W | FE models; OP2 results as Fields | Build | 3 | FLX |
| OpenFOAM case | [unverified] | R/W | Mesh, conditions, fields; OpenFOAM itself only as an External Op | Build | 4 | FLX, COV |

**Decision D-ECO-4:** Formats built on HDF5 (CGNS, Exodus II, VTKHDF) wrap the reference C libraries compiled to Wasm components, with HDF5 object time tracking disabled so writes are deterministic [unverified: HDF5 property name and completeness]. *Why:* HDF5 is a large binary container whose reference library is the only complete implementation, and compiling it to Wasm keeps browser parity. *Rejected:* a pure Rust HDF5 subset (large effort, phase 5 at best, revisited if the wrapped library blocks determinism); native libraries (break browser parity).

### Manufacturing, metrology, systems and materials

MFG owns manufacturing semantics, ELX systems and robotics, COV materials.

| Format | Version | R/W | Level | Phase | Owner |
| --- | --- | --- | --- | --- | --- |
| G-code | ISO 6983-1:2009 per MFG; dialects per `Controller` | W; R to verify and migrate | As the dialect allows | 2 | MFG |
| Tool data | ISO 13399 inside vendor catalog packages; DIN 4000 mapping [unverified]; documented CAM tool libraries [unverified which] | R | Tool Assemblies; holders as collision Bodies | 2 | MFG |
| Presetter readings | Per connector | R | Length, radius, runout as signed External inputs by tool serial | 2 | MFG |
| QIF | QIF 3.0, ISO 23952:2020; DMSC Model-Based Characteristics 1.0 an ANSI standard since 24 June 2026 [QIF site] | R/W | Characteristics, plans, results | 2 (characteristics), 3 | MFG |
| DMIS; MTConnect | DMIS [unverified]; MTConnect 2.5.0 [MTConnect 2.5.0] | W, R; R | Programs and results; machine state as External inputs | 3 | MFG |
| OPC UA for Machine Tools | OPC 40501-1 release 1.02.0, published 1 November 2024, as MFG states [OPC 40501-1 v1.02] | R; jobs only by transfer Acts, never `Start` | Machine state | 3 | MFG |
| ReqIF; SysML v2 and the Systems Modeling API | ReqIF 1.2 [ReqIF]; SysML 2.0, KerML 1.0, API 1.0, adopted 21 July 2025 [OMG SysML v2] | R/W | Requirements; models mapped to `std::systems` | 4 | ELX |
| URDF; SDFormat; MJCF | Per ELX [unverified versions] | W; R | Kinematic trees, inertials, sensors | 4 | ELX |
| MatML | [unverified] | R/W | Property records with units and sources | 2 | COV |

All rows here are Build. Crucible never reverse-engineers a proprietary format or imports feature history (D-ECO-25).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| STEP layer 1: Part 21 | Generated reader and writer; late-bound long-tail access | `ImportError::Unreadable { location }` | ECO-O-23, ECO-O-5 | 1 |
| STEP layer 2: schema rules | Generated checkers on every export | `ExportError::SchemaRule { rule, instance }` | ECO-O-3 | 1 |
| STEP layer 3: AP242 mapping | Geometry, structure, validation properties, PMI write; AP203 and AP214 read | Report entries per entity | ECO-O-1, ECO-O-2 | 1 |
| AP242 PMI read, persistent ids, tessellation | Per recommended practice | Report entries | ECO-O-2, ECO-O-24 | 2 |
| 3MF and STL | Core, Production, Materials, Beam Lattice | `ExportError` for unsupported extensions | ECO-O-16 | 1 |
| Licensed MCAD translators | Mechanical table rows | Unqualified versions flagged | ECO-O-15 | 2 |
| Board exchange for mechanical teams | IDF, STEP boards and IDX baselines to a read-only board Part, which MEC's enclosure checks (clearance, cut-outs, keep-ins) use | `ImportError` naming the missing data | ECO-O-26 | 2 |
| Board fabrication and assembly writers | Gerber, XNC, IPC-2581C, ODB++, IPC-D-356, placements from ELX's model | `ExportError` listing missing board data | ECO-O-25 | 3 |
| IDX change proposals | Incremental exchange with responses | Rejected proposals reported | ECO-O-16 | 4 |
| HDF5-based formats | Wrapped library, deterministic writes | `ExportError::Nondeterministic` | ECO-O-4 | 4 |
| Remaining catalog rows | Per table row | Report rules; conflicting tool-table entries fail the build (MFG) | ECO-O-16 | 2 to 5 per row |

## Translator quality

A translator ships only when independent oracles show it keeps its catalog row's promise. Five layers do this: interoperability testing, validation properties, round trips, differential testing and fuzzing.

### CAx-IF participation

The CAx Implementor Forum belongs to the MBx Interoperability Forum of AFNeT, PDES, Inc. and prostep ivip [MBx-IF]. Round 58J ran from March to September 2026, covering assembly-level semantic PMI, composites, kinematics, persistent ids, holes, threads and Model Based Notes [CAx-IF 58J]. Vendors check files with NIST's STEP File Analyzer and Viewer, and results compare native with target statistics.

**Decision D-ECO-5:** Crucible joins the MBx Interoperability Forum in phase 1 and takes part in every CAx-IF round from then on, beginning with geometry, assembly and PMI-write test cases. Every round's results become regression oracles. *Why:* the forum is where AP242 implementers agree on recommended practices and find each other's bugs; no in-house test replaces testing against CATIA, NX, Creo and other systems' real output. *Rejected:* testing only against public sample files (misses current practices and edition 4 features); waiting for a mature translator before joining (delays the bugs that matter most).

### Validation properties and corpora

In the CAx-IF practice, version 4.6, a sender writes properties of solids, free geometry and assemblies, so a receiver can check what it read [CAx-IF GVP]:

| Property | Interoperability testing (green / yellow / red) | Industry production |
| --- | --- | --- |
| Volume, area, curve length | Below 1% / 1–10% / above 10% | 0.5% |
| Centroid | Below 1 mm / 1–5 mm / above 5 mm, or 0.1% / 1% of the box diagonal | 0.02 mm plus 0.1% for models over 20 mm |
| Bounding box | Absolute error of both corners | 0.5% |

Exports write these properties from Anvil's certified integration, and imports check them. On the STEP corpus the production thresholds are the pass line, with 0.05% on volume and area as the internal target. Properties miss slivers and say nothing about PMI, so round trips and item-by-item PMI comparison cover the rest.

| Corpus | Contents | Access |
| --- | --- | --- |
| NIST MBE PMI test cases | CTC-01 to 05, FTC-06 to 11, STC, HTC; AP242 and AP203 files with native CATIA V5, NX, Inventor, Creo and SOLIDWORKS models [NIST MBE PMI] | Public |
| CAx-IF round files | Current-practice files from many systems [CAx-IF 58J] | Members [unverified terms] |
| ABC dataset | One million Onshape models with STEP, Parasolid, meshes and FeatureScript [ABC] | Testing only, never redistributed |
| Held-out corpus; format suites | Models never shown to agents; 3MF samples, Reference FMUs, SSP and buildingSMART examples, KiCad demos | Protected store; public [licences unverified] |

### Round trips, fuzzing and qualification

All topology comparisons use Anvil's topology normal form on both sides (ANV-O-NF-1).

| Suite | Pass line | Phase |
| --- | --- | --- |
| Self round trip: write, read back | Analytic and NURBS geometry bit-identical; procedural geometry equal to its recorded B-spline approximation within the stored bound; topology equal in normal form; persistent ids and PMI preserved | 1 |
| External round trip through CAx-IF ping-pong cases | Validation properties within production thresholds; persistent ids match; partner edits appear as a diff | 2 |
| Differential read against Open CASCADE 8.0.1 [OCCT releases] and, from phase 2, a licensed translator | Topology equal in normal form, seam and pole counts reported separately; Hausdorff distance under the larger file tolerance; every disagreement triaged | 1 |

Open CASCADE runs only as an external oracle in CI. Readers are fuzzed with structure-aware mutators and grammar-based generators for Part 21, XML and S-expressions. Each release needs 10⁹ executions per reader without a new crash (target).

A licensed translator version is qualified before an organization can pin it. The NIST native files and the held-out native corpus run through it, and a signed record keeps topology counts, validation-property deviations and PMI statistics. Builds show that record beside every External input the translator produced.

Translators are versioned packages: an output change is labelled (D-ECO-14), and pinned versions re-export identically.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| CAx-IF participation | Every round; results become regression oracles | A regression blocks the translator release | ECO-O-1, ECO-O-2 | 1 |
| Validation properties | Written from certified integration; checked on import | `Warning` Check beyond production thresholds | ECO-O-1 | 1 |
| Round trips in normal form | The three suites above | A self round-trip failure blocks release; differential disagreements triaged | ECO-O-24 | 1, 2 (external) |
| Reader fuzzing | Continuous, per reader | A new crash blocks release | ECO-O-5 | 1 |
| Licensed translator qualification | Signed record per version | Unqualified versions cannot be pinned | ECO-O-15 | 2 |
| Translator versioning | Output changes labelled; pinned versions re-export identically | Unlabelled output changes refused | ECO-O-10, ECO-O-22 | 1 |

## The extension model

### Tiers and contexts

Contract section 4 fixes three tiers: Ingot packages, Wasm components and operations in Anvil and Flux. Wasm components, written in Rust first, carry importers, nesting, toolpath strategies, specialist solvers, panels and connectors. A third party contributes an operation through the same RFC and review process the core team uses.

**Decision D-ECO-6:** Authors choose the tier by a fixed rule. Use Ingot unless the code needs one of: more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express efficiently; then use a Wasm component. Promote to an in-tree operation only when at least three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives. *Why:* most logic stays in the most reviewable, most composable tier, and the core grows only where reuse is proven. *Rejected:* letting authors pick freely (heavy code lands in Ingot and slows builds, or trivial logic lands in opaque Wasm components); a native plugin tier (unsafe, per-OS, impossible in the browser).

Wasm components are CPU-only; GPU work lives in operations, which they call through `crucible:ops`.

| Context | Runs | May import | Never imports | Output enters |
| --- | --- | --- | --- | --- |
| Evaluation | Inside Kiln as an Op | `crucible:ops`, `geom`, `field`, `model`, `host`, type-only `crucible:` interfaces | Every `wasi:` interface, `crucible:api` | Kiln, under the Op's key |
| Panel | In the app, within UIX's frame budget | `crucible:api/read`; `crucible:api/edit` when granted | Clocks, randomness, files, network | `api` calls; edits record the package in `ChangeProvenance` |
| Tool | In a tool runner | `crucible:api`, `wasi:filesystem` on granted directories, `wasi:clocks`, `wasi:random`, `crucible:tool/process` | Network unless granted as a connector | External inputs, `api` calls |
| Connector | On a team server or desktop | `crucible:api` scoped to its record types, `wasi:http` to declared hosts, `wasi:clocks`, `wasi:random`, `crucible:connect` | Files, process spawning | External inputs, events, Acts |

The registry checks imports against the context at publish and the host again at instantiation. UIX renders panels inside a frame that shows the package identity.

### Isolation and platforms

**Decision D-ECO-26:** Only first-party Wasm components built by the registry's hermetic builder run inside the engine process. Every third-party Wasm component, including a user's own unpublished one, runs in a worker process under PLT's OS sandbox (AppContainer, App Sandbox, or seccomp with Landlock) that holds no tokens, repository handles or signing keys and receives only its call's inputs. On servers, workers are per (tenant, label scope); `export_controlled` scopes get dedicated VMs, and Wasmtime pooling slots are never reused across tenants or scopes. *Why:* the engine process holds every open repository, the user's tokens and the device signing key, so Wasmtime would otherwise be the only boundary; its April 2026 advisories include an out-of-bounds write in string transcoding and data leakage between pooling-allocator instances [Wasmtime GHSA-394w][Wasmtime GHSA-6wgr]. *Rejected:* in-process execution for verified publishers (round 1; verification establishes identity, not memory safety); one worker pool for all tenants (a pooling leak would cross tenants).

PLT applies Wasmtime security releases within 7 days on every supported line (D-PLT-21), each gated by ECO-O-6. Proposal CI from agent and external branches runs on the untrusted-evaluation workers of contract section 7.8.

| Platform | Engine |
| --- | --- |
| Windows, macOS, Linux; servers | Wasmtime LTS with Cranelift in `wasm-host` (PLT) |
| Desktop browsers | The browser's WebAssembly engine through one first-party Wasm component runtime (D-ECO-10) |
| iPadOS | WebKit, with Pulley as fallback (contract section 7.4); std and first-party Wasm components inside the app binary |
| Android tablets | Wasmtime, which rates `aarch64-linux-android` Tier 3 [Wasmtime tiers]; Google Play allows downloaded code run by a virtual machine or interpreter with indirect access to Android APIs [Google Play DNA], so no world imports an Android API |

Tool and connector Wasm components run locally on desktops and on the server for browsers and tablets; only the location differs.

On iPadOS, registry packages appear only as dependencies of an opened design, since guideline 3.2.2(i) rejects store-like catalogs of extensions [App Review]. The registry meets guideline 4.7 for them with an index and universal links (4.7.4), reporting and blocking (4.7.1) and age ratings (4.7.5), and paid packages follow guideline 3.1. First-launch downloads show their size (4.2.3(ii)), and designs evaluate remotely if review rejects downloads.

**Decision D-ECO-10:** The registry ships determinized core modules plus a data description of each Wasm component, never per-component JavaScript. Browsers instantiate them through one first-party, generic Wasm component runtime that lifts and lowers the Canonical ABI from that description. Third-party Wasm components run in a separate cross-origin, sandboxed worker with no OPFS, cookies or credentials, exchanging data by `postMessage`, and an oracle compares every browser result with the native one. *Why:* generated glue would run in the engine worker's origin, with access to every local repository, authenticated `fetch` and WebCrypto keys, so the glue, not Wasm, would be the boundary; a fixed runtime is reviewed once. *Rejected:* per-component ES modules as jco generates them [jco]; transpiling in the client (the same glue, more variance); Pulley compiled to Wasm (an interpreter inside an engine). (revised in round 2)

PLT owns the web app's integrity: an asset manifest in a transparency log, TUF checks in the service worker, and expiring apt and dnf metadata.

### First-party WIT packages

Each package is versioned with SemVer [WIT guide] and published in the registry.

| WIT package | Interfaces | Worlds | Owner |
| --- | --- | --- | --- |
| `crucible:units` | `si`: aliases such as `length`, each an SI `f64` | | ECO, ING |
| `crucible:ops` | `anvil`, `flux`, generated from the operations catalogs | | ANV, FLX |
| `crucible:geom` | `types`, `build`, `measure` | | ANV |
| `crucible:field`; `crucible:model` | `types`, `build`, `sample`; `types`, `build`, `read` | | FLX; MEC, KLN |
| `crucible:host` | `diagnostics`, `progress` (write-only), `cas`, `parallel` | | KLN |
| `crucible:io` | `types`, `read`, `write` | `importer`, `exporter` | ECO |
| `crucible:physics`; `crucible:material` | `solve`; `constitutive` | `solver`; `constitutive-model` | COV, FLX |
| `crucible:mfg` | `strategy`, `post` | `toolpath-strategy`, `post-processor` | MFG |
| `crucible:ui` | `panel`, `canvas2d` | `panel`, `canvas2d` | UIX |
| `crucible:api` | One interface per method group | | AGT |
| `crucible:tool` | `process`, `external` | `driver` | ECO, PLT |
| `crucible:connect` | `types` (offers, quotes, orders), `secrets`, `partner`, `erp`, `mes`, `plm` | `connector`, `partner-connector`, `erp-connector`, `mes-connector`, `plm-connector` | ECO, MFG, KLN |

**Decision D-ECO-7:** Every first-party WIT package uses the `crucible:` namespace, one package per domain, with American spelling. Operations are reached through one package, `crucible:ops`, with one generated interface per catalog (`crucible:ops/anvil`, `crucible:ops/flux`), and `crucible:geom` holds only types, builders and measurement. Constitutive models use `crucible:material/constitutive`, specialist solvers `crucible:physics/solver`, and panels `crucible:ui/panel`. *Why:* one namespace makes ownership obvious; one operations package gives every Wasm component, ELX's placer included, both engines' operations; two names for one interface would split the ecosystem. *Rejected:* per-subsystem namespaces such as `flux:` and `anvil:`; operations inside `crucible:geom` (round 1; no home for Flux operations). (revised in round 2)

No `crucible:` package freezes before the names clear (contract section 13.1), and `crucible:ops/flux` takes the physics engine's final name. Units cross the boundary as SI `f64` checked against the `crucible:units` aliases, while the generated Ingot wrapper carries `Quantity<D>`. Strings a Wasm component authors become `ExternalText` with the package as origin.

### WIT example: an importer

The importer reads an Asset through a random-access host resource, which zip-based formats need, and emits entities through builders, so Anvil decides validity.

```wit
package crucible:io@1.0.0;

interface types {
    use crucible:geom/types@1.0.0.{error-bound, heal-policy};
    use crucible:units/si@1.0.0.{length};

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
    use crucible:model/build@1.0.0.{model-builder};
    probe: func(head: list<u8>) -> option<format-info>;
    /// Every source entity must appear in `read-result.entries`.
    parse: func(src: borrow<source>, options: read-options, out: borrow<model-builder>)
        -> result<read-result, import-error>;
}

world importer {
    import types;
    import crucible:geom/build@1.0.0;      // B-rep, mesh and point builders, validated by Anvil
    import crucible:model/build@1.0.0;
    import crucible:host/diagnostics@1.0.0;
    export read;
}
```

The `exporter` world mirrors it, writing from a read-only `model-view` into a `sink` that becomes a CAS blob.

### Capabilities

A Wasm component can call only what its world imports. The manifest scopes each import (HTTP hosts, filesystem roots, `api` scopes, named secrets). A person grants each scoped capability per package, and `ingot.lock` records the grant.

Organization policy allows or denies publishers, capabilities and licences, and can disable the connector context. Evaluation Wasm components need no grants, because nothing they import has an effect.

**Decision D-ECO-27:** A Wasm component may hold at most one of three capabilities unless a `policy:admin` grants a named exception: reads of data labelled above `public` through `crucible:api`; network egress; filesystem writes outside CAS. Connector `api` scopes narrow to their record types (`catalog:read`, offer writes) and never include design reads, and an outbound request that carries data derived from labelled reads goes through a `release_data` Act (D-ECO-28). Grant screens state combinations: "can read your designs and send data to api.supplier.com". *Why:* two grants that each look harmless combine into an exfiltration channel, and per-capability screens never showed the combination. *Rejected:* per-capability grants without a flow rule (round 1); taint tracking inside Wasm components (unverifiable in the sandbox).

An update that adds a capability or changes the signer waits as a Proposal while Kiln builds with the pinned version. The host reaches only declared hosts and granted directories, and attaches a named secret only to requests for its declared host. Revoking a grant stops running instances with `CapabilityDenied { capability, package, fix }`, and every tool and connector call is audited with the package identity.

### Determinism and limits

Contract section 7.4 states the rules. PLT owns the determinizer, its fuel table and its overhead targets: scalar-float Wasm components ≤ 10%, SIMD-float ≤ 25%, metering ≤ 10%. ECO adds three rules for Wasm components:

1. Randomness comes only from a seed that Kiln derives from the Op's inputs.
2. `OutOfFuel`, `StackLimit` and `MemoryLimit` are cached `Failure`s; host resource errors and cancellation are Aborts.
3. Data parallelism uses `crucible:host/parallel`, which returns outputs in input order.

**Decision D-ECO-8:** Evaluation-context Wasm components execute only as determinized binaries. The registry runs PLT's determinizer at publish, the local toolchain runs the same version at build for unpublished Wasm components, and the determinized binary's SHA-256 enters the `OpKey`. *Why:* engine-independent instrumentation gives identical results and trap points in Wasmtime, WebKit and every browser engine, as `wasm-instrument` and finite-wasm do for metering [wasm-instrument][finite-wasm]; determinizing once per binary means every client runs the same bytes. *Rejected:* engine fuel (absent from browsers); wall-clock timeouts (nondeterministic); instrumenting on each client at install (a second producer of executed bytes, with no single hash per Wasm component). (revised in round 2)

**Decision D-ECO-9:** Evaluation worlds are synchronous: no `async` functions, streams or futures, and no WASI imports. Tool and connector worlds use WASI 0.3's native async functions, `stream<T>` and `future<T>` [WASI 0.3][WIT guide]. *Why:* evaluation inputs already sit in CAS, so concurrency inside a pure function adds scheduling nondeterminism and nothing else; keeping WASI out of evaluation also insulates the evaluation ABI from the WASI release train. *Rejected:* async evaluation worlds with a deterministic host scheduler (complex to specify and verify, no measured benefit); WASI 0.2 for tool and connector worlds (superseded; its `pollable` model had the composition problem that 0.3 fixes [WASI 0.3]).

Limits apply per call; a manifest may request more, up to the organization's ceiling, and PLT reserves declared memory before instantiation.

| Limit | Evaluation default (ceiling) | Tool and connector default | Failure |
| --- | --- | --- | --- |
| Linear memory | 256 MiB (4 GiB) | 2 GiB | `MemoryLimit`, deterministic |
| Fuel | 5 × 10¹⁰ units, roughly 10 to 30 s native (policy) | Wall-clock budget | `OutOfFuel`, deterministic |
| Logical stack | 256 KiB (1 MiB, calibrated in phase 0) | Engine default | `StackLimit`, deterministic |
| Output; handles; binary | 2 GiB per output; 10⁷ handles (10⁸); 64 MiB (256 MiB) | Policy; 10⁶; 64 MiB | `OutputLimit`, `HandleLimit`, refused at publish |
| Wall clock | None, cancellation only | 15 min per call | `Timeout`, never cached |

Work above 4 GiB uses PLT's chunked buffers, operations or server-side tool-context Wasm components; 64-bit memories stay off while browsers cap them [Wasm 3.0].

### Versioning

WIT packages follow SemVer with feature gates: `@since` items never change incompatibly, `@unstable` items may vanish, and `@deprecated` pairs with another gate [WIT gates]. Five rules follow:

1. A 1.x package only adds items, and unstable features are opt-in and publish only in pre-releases.
2. Deprecation lasts at least 24 months and one edition, and a new major ships an adapter implementing the old world.
3. Every world major stays executable for 10 years after it is superseded (target).
4. No engine upgrade ships unless every registry test vector's hash is unchanged.
5. If the Component Model encoding changes before 1.0 [unverified: status], the registry re-encodes stored Wasm components, proves identical results and keeps the original hash as identity.

WASI 0.3.0 shipped on 11 June 2026 and 0.3.1 on 11 August 2026, with no date for 1.0 [WASI roadmap]. Wasmtime 46 first implements final 0.3.0 [WASI 0.3]. Only tool and connector Wasm components track this train, and the host supports the current and previous 0.3.x releases.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Contexts and worlds | Imports checked at publish and instantiation | `ForbiddenImport { import, fix }` | ECO-O-8 | 0 |
| First-party WIT packages | `crucible:` at 0.x; frozen only after names clear | Unstable items need opt-in | ECO-O-6 | 0 |
| `crucible:ops` | Generated `anvil` and `flux` interfaces; recorded Op dependencies | `OpVersionRetired` with an upgrade Proposal | ECO-O-6 | 1 (`anvil`), 2 (`flux`) |
| Process isolation | Third-party Wasm components in sandboxed workers; per (tenant, label scope) on servers | Worker loss is an Abort | ECO-O-8 | 1 |
| Capability grants and flow rule | Scoped grants; at most one of labelled reads, egress and file writes | `CapabilityDenied { capability, package, fix }` | ECO-O-8 | 1 |
| Determinized execution and limits | Contract section 7.4; seeds from inputs; limits above | Limit failures as cached `Failure`s | ECO-O-6, ECO-O-7 | 0 |
| Browser Wasm component runtime | Generic runtime; third-party Wasm components cross-origin | Without isolation, third-party Wasm components run remotely | ECO-O-6, ECO-O-8 | 1 |
| Tablet execution | WebKit with bundled std; Android without Android API imports | Rejected downloads evaluate remotely | ECO-O-6 | 3 |
| WIT versioning | Additive minors, deprecation window, adapters, retention | A removal in a minor is refused | ECO-O-10 | 0 |

## SDKs, CLI, events and integration

AGT's method catalog is the only programmatic surface (D-AGT-1); ECO packages it and adds events, exit surfaces and enterprise connectors.

### SDKs, methods and the CLI

| SDK | Form and distribution | Phase |
| --- | --- | --- |
| Rust | `api` types with HTTP and in-process clients; crates.io as `crucible-sdk` | 0 |
| Python | Pure Python generated from the catalog's JSON Schemas; PyPI as `crucible` with PEP 740 attestations [PEP 740] | 1 |
| TypeScript | Pure TypeScript for Node.js, Deno, Bun and browsers; npm as `@crucible/sdk` through trusted publishing [npm security plan] | 2 |
| C ABI | `libcrucible` for C, C++, C#, Java, Julia, MATLAB and CAD add-ins; archives per Tier 1 target | 2 |

Package names depend on availability on each index [unverified].

**Decision D-ECO-11:** The official SDKs are Rust, Python, TypeScript and a C ABI. Every other language binds the C ABI or generates a client from the published JSON Schemas and OpenAPI 3.1 description. *Why:* these four cover systems code, scripting and notebooks, web and agents, and every language with a foreign-function interface; each extra official SDK multiplies parity testing. *Rejected:* official Java, C# and Julia SDKs at launch (the C ABI and generated clients serve them with less upkeep); a Python SDK built on native extensions (AGT keeps the SDKs pure-language so they run wherever their runtimes run).

SDK versions equal the catalog version. A method is deprecated for at least 12 months before a major removes it, and servers serve the previous major for 24 months.

The C ABI passes canonical JSON through `crucible_call(client, method_id, request, &response)`, streams Evaluations through `crucible_call_stream`, and maps CAS objects with `crucible_cas_map`. Its handles are opaque, panics never cross it, and symbols are only added within a major; removal needs a new library name (`libcrucible2`).

Every method is `<group>.<name>` in the contract's eight groups (section 7.6). ECO asks AGT to add:

| Method | Contract | Failure |
| --- | --- | --- |
| `read.packages`, `read.package` | Search by name, world, tag, licence or badge; one package's manifest, capabilities, signer, badges, advisories and output-change labels | `package.not_found` with nearest names |
| `compare.resolve` | Manifest plus lockfile → new lockfile and diff, not applied | `package.unsatisfiable` with the PubGrub explanation |
| `edit.grant_capability`, `edit.revoke_capability` | A scoped grant or revocation recorded in `ingot.lock` | `policy.denied` naming the rule |
| `read.events`, `read.subscribe`, `read.unsubscribe` | Events by cursor; webhook subscriptions, created only by people with `maintainer` or `admin` | `events.cursor_expired`; `events.url_refused` |
| `edit.import_archive` | Repository archive File → design repository | `archive.incomplete` listing missing objects |
| `read.registry_bundle` | Lockfile → signed offline bundle of its pinned packages | `package.unavailable` |

Publishing, yanking, deprecating and every export are Act classes (AGT).

The `crucible` CLI maps subcommands one-to-one onto methods, with aliases for daily work. For licensed formats, `crucible import` first records the External input. `crucible update parts` refreshes only catalog-part data pins and lists every substitution a `CatalogSelection` makes, and `crucible publish` is an Act.

Output is human-readable, or canonical JSON with `--json`. Exit codes are 0 success, 1 Check failures, 2 usage, 3 build error, 4 authorization and 5 infrastructure, and `--offline` turns any network need into a typed error.

### Events and webhooks

**Decision D-ECO-12:** ECO owns the event envelope, delivery and signing for every tab. Events use the CloudEvents 1.0 envelope; webhooks follow the Standard Webhooks specification, signed with Ed25519 (`v1a`) by default; payloads are thin: identifiers, hashes and a link, never design content. Other tabs define event types, and KLN's per-repository sequence number travels as the CloudEvents extension attribute `seq`. *Why:* both are open specifications with receiver libraries; asymmetric signatures let receivers verify without a secret that could forge events; thin payloads mean a leaked endpoint reveals no design data. *Rejected:* a custom envelope (no tooling); HMAC-only signing (every receiver holds a forging secret); fat payloads (data bypasses access control); per-tab envelopes (round 1, where two tabs contradicted each other). (revised in round 2)

CloudEvents requires `id`, `source`, `specversion` and `type`, with `source` plus `id` unique, and extension names in lowercase letters and digits [CloudEvents]. `source` is the repository, registry or catalog URI and `type` a reverse-DNS name such as `dev.crucible.proposal.opened` [unverified: domain]. KLN defines repository, lifecycle and evaluation types, AGT the Act types, and ECO registry and catalog types such as `package.yanked` and `offer.changed`.

1. **Pull.** `read.events` returns events in per-source order, retained at least 30 days (target); CI uses this path.
2. **Push.** Deliveries carry `webhook-id`, `webhook-timestamp` and `webhook-signature` over id, timestamp and payload; HMAC-SHA256 (`v1`) serves receivers that cannot verify Ed25519 [Standard Webhooks spec]. Receivers reject timestamps over 5 minutes old.
3. **At least once.** Receivers deduplicate by `webhook-id`, equal to the CloudEvents `id`. Retries use exponential backoff with jitter over about three days, following the specification's example [Standard Webhooks spec], then a dead-letter queue that administrators see.
4. **SSRF protection.** URLs must use HTTPS and must not resolve to loopback, link-local or private ranges unless a self-hosted policy names internal hosts [Standard Webhooks].
5. **People only.** Only people create subscriptions; agents receive the same events as MCP resource subscriptions (AGT).

### Exit surfaces

- **Repository archive** (phase 1): a design repository's full history, with every Change, branch, release signature, lockfile and the CAS objects needed to rebuild. Restoring it elsewhere reproduces every Change's build hash.
- **Release bundle** (phase 1): a release's neutral Files, the BOM as CSV and JSON, and the signed manifest.
- **Git mirror** (phase 2): Ingot sources, manifests and lockfiles, one Git commit per selected Change.

The archive format and the CAS encoding are open, so a third party can write an independent reader (ECO-O-12).

**Decision D-ECO-28:** Every ECO surface that moves tenant bytes outside the tenant is an Act in AGT's `release_data` family, `{ recipient, payload, purpose, authorization }`: archive export, each Git mirror push, release-bundle delivery, partner quote requests, enterprise-connector messages, passport publication and package publishing. At commit each runs the same checks: labels against recipient attributes, restricted-party screening, an export authorization record (licence number, exception or exemption) for `export_controlled` payloads, and a watermark record, expiry and audit entry. *Why:* six exit paths with different controls leave the weakest one open; one family gives one review page and one audit trail, and contract section 7.6 already makes export an Act. *Rejected:* plain API methods for archive export and mirroring (round 1); controls per exit path (they drift).

### Enterprise connectors

**Decision D-ECO-30:** ERP, MES and PLM systems connect through connector worlds in `crucible:connect` (`erp-connector`, `mes-connector`, `plm-connector`). Field mappings are Ingot data packages, and a field-ownership table states which system owns each field. Outbound messages are `release_data` Acts; inbound data arrives as signed External inputs. *Why:* integration is bidirectional and field-mapped, and mappings as data are versioned, reviewed and tested like any package. *Rejected:* a webhook consumer that only reads change notices (round 1; nothing flows back); integration code per customer in the core.

Outbound records are `ItemMaster`, `BillOfMaterials`, `Routing` and `ChangeNotice`. A BOM line carries find number, quantity with unit, reference designators, effectivity, phantom flag and substitute group. Routings carry operations, work centres, setup and run times and tooling, and change notices carry effectivity and disposition per stock location.

Inbound External inputs carry standard cost, purchase price, lead time and inventory for MFG's cost models. Messages follow OAGIS business object documents for ERP and ISA-95 (IEC 62264) B2MML for MES [unverified: current versions].

| Field | Owner by default |
| --- | --- |
| Item number, revision label, lifecycle state | Crucible, or the external PLM under KLN's subordinate system-of-record policy |
| EBOM structure, reference designators, effectivity | Crucible (KLN) |
| MBOM and routings | Crucible (MFG) where it plans manufacturing, else the ERP |
| Cost, price, lead time, inventory | ERP, inbound |
| Stock disposition on change | Crucible decides; the ERP executes |

KLN owns the system-of-record policy per record type (`Crucible` or `External(connector)`). Under `External`, numbers come through the PLM connector. The release Act publishes a release package into the external item revision: AP242 with PMI, PDF drawings, BOM, NC programs and an Ingot source archive with its digest.

External approvals return as signed External inputs naming the Crucible content digest, so approval still binds to content (D-KLN-28). Reference connectors for one large ERP, one open-source ERP, two enterprise PLM systems and one cloud PLM arrive in phase 2 [unverified: API names].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| SDKs and C ABI | Generated from one catalog | AGT's error object in every language | ECO-O-11 | 0 (Rust), 1 (Python), 2 |
| ECO's API methods and CLI | Methods above; aliases, exit codes, offline mode | Typed errors; exit codes 1 to 5 | ECO-O-11 | 1 |
| Events and webhooks | CloudEvents; Standard Webhooks, Ed25519 by default; at least once | `events.cursor_expired`; retries, then dead-letter queue | ECO-O-14 | 1 |
| Repository archive and open encodings | Full history; independent readers possible | `archive.incomplete` | ECO-O-12 | 1 |
| Outbound Acts | `release_data` checks at commit for every exit path | `label.write_down`; screening or authorization failure | ECO-O-28 | 1, 2 (mirror, connectors) |
| ERP and MES connectors | Mapped records out; External inputs in; field ownership | `MappingConflict { field, owner }` | ECO-O-27 | 2 |
| PLM subordinate mode | External numbering; release packages out; signed approvals in | `DigestMismatch { expected, found }` | ECO-O-27 | 2 |

## Package registry

The registry distributes every package, from std and translators to solvers, panels, templates and catalog-part definitions. The core team publishes through it like anyone else (Principle 1).

Phase 1 ships a signed first-party index of std, `crucible::` packages and translators, built by the hermetic builder and served as TUF targets. The public registry with trusted publishing opens in phase 2 (contract section 13.2).

### Names and namespaces

**Decision D-ECO-13:** Every package lives in a namespace that a verified publisher owns, and its name is `namespace::name`, the path Ingot uses in `use`. Domain claims own bare names; code-host claims take a mandatory prefix (`gh_<org>`, `gl_<org>`), and individual accounts get `u_<handle>`, so the three kinds never collide. *Why:* code-host organization names are first-come, so whoever registers a GitHub organization `acme` first could take the name acme.com's owner needs; Maven Central reuses DNS in reverse and grants code-host namespaces only for personal usernames [Maven Central namespaces]. *Rejected:* a flat namespace (squatting and typosquatting); optional scopes (the unscoped majority keeps the problem); unprefixed code-host claims (round 1; they collide with domain owners). (revised in round 2)

| Rule | Detail |
| --- | --- |
| Syntax and spellings | Segments match `[a-z][a-z0-9]*(_[a-z][a-z0-9]*)*`. One name, three spellings: Ingot `parts::ti::tps62133`, WIT `parts:ti-tps62133`, URL `parts/ti/tps62133`; a WIT collision is refused |
| Reserved | `std`, `crucible`, `core`, `parts`, `examples`, `wasi`, `test`, and the prefixes `u_`, `gh_` and `gl_` outside their claims |
| Look-alikes and new versions | Names within edit distance 1 of a popular one, or equal after mapping look-alikes, are held for review whatever the publisher's status; new versions resolve for others only after 72 h, as KLN's policy sets |
| Re-verification and transfer | Domain claims are re-verified yearly with DNS control plus an existing publisher credential, so a re-registered domain cannot take over; transfers need consent or the dispute policy and are logged |

### Manifest, lockfile and compatibility

A package and a design repository share `ingot.toml` and `ingot.lock`; ING owns the language keys and the module system.

```toml
[package]
name    = "acme::radiation"
version = "1.4.0"
edition = "2027"
license = "Apache-2.0"

[components.view_factors]
world   = "crucible:physics/solver@1.0.0"
context = "evaluation"
fuel    = 2e11                           # must fit the organization ceiling

[components.vendor_sync]
world   = "crucible:connect/connector@1.0.0"
context = "connector"
http    = ["api.acme.example"]           # the only reachable host
secrets = ["acme_api_token"]
```

For each resolved package the lockfile records name, exact version, registry and granted capabilities. It also records the SHA-256 of the source archive and of each determinized binary, and the signer identity (OIDC issuer and subject) with the signature bundle's digest. Assets and External inputs are pinned too.

A signer change needs human approval like a capability escalation, and an entry whose registry changes fails resolution. Resolution uses PubGrub, whose derivation tree becomes a typed explanation with fixes [PubGrub].

At publish the registry measures three kinds of change against the previous version. Incompatible interface changes are refused in minors and patches, as cargo-semver-checks does for Rust [cargo-semver-checks]. Changed outputs of examples and test designs are recorded, and so are changed `EntityId`s that public features produce on test designs.

Registry packages carry only text, and `OpSite` derives from text (contract section 5), so entity names do not depend on how a package was edited.

**Decision D-ECO-14:** A release may change outputs or entity names, but the registry measures and publishes every such change, and `crucible update` shows it before applying. A patch release that changes outputs is labelled "output-changing", a release that renames entities on test designs is at least a minor labelled the same way, and organizations can block such updates by policy. *Why:* in physical design a fix that moves geometry is a design change, and a renamed entity breaks anchors, PMI and review comments in every dependent design. *Rejected:* trusting authors' version numbers alone (silent geometry changes); forbidding output changes outside majors (fixes would wait for breaking releases). (revised in round 2)

### Publishing and signing

**Decision D-ECO-15:** Publishing never uses long-lived tokens. A package is published either from CI through trusted publishing, which exchanges the CI's OIDC identity for a short-lived credential, or interactively with phishing-resistant two-factor authentication. Publishing is an `api` Act, so it is audited like any other external effect. *Why:* crates.io and npm introduced trusted publishing in July 2025 [crates.io update 2025-07][npm security plan]; after the Shai-Hulud worm spread through compromised maintainer accounts in September 2025, GitHub narrowed npm publishing to trusted publishing, local publishing with 2FA and short-lived tokens [npm security plan]. *Rejected:* API tokens with long lifetimes (the main theft target in registry compromises); publishing without 2FA (account takeover).

The pipeline runs in order, and a failure at any step returns a typed error with nothing published:

1. Verify the signer against the namespace policy, and the version's novelty.
2. Rebuild hermetically where the toolchain allows.
3. Determinize evaluation Wasm components (D-ECO-8).
4. Run scanners and the export-classification check (D-ECO-29).
5. Run domain acceptance checks contributed as data, such as COV's validity-envelope checks.
6. Measure interface, output and entity-name changes (D-ECO-14).
7. Run test vectors on every engine (ECO-O-6).
8. Sign the index entry and append it to the log.

[[DIAGRAM: Publish pipeline, left to right: CI or client with OIDC trusted publishing → signer and namespace check → hermetic rebuild → determinize (PLT) → scanners and export classification → domain acceptance checks → interface, output and entity-name diffs → test vectors on all engines → sign and append to log. Each box branches to "typed error, nothing published". Below, desktop, iPadOS and browser clients verify signer identity, TUF metadata and log inclusion.]]

| Layer | Mechanism | Proves |
| --- | --- | --- |
| Author signature | Sigstore keyless signing: a short-lived Fulcio certificate bound to the OIDC identity, logged in Rekor [Sigstore] | Who published these bytes |
| Namespace policy | The owner's offline key signs the trusted publishers (OIDC issuer and subject pattern) as delegated TUF targets | Who may publish here |
| Build provenance | SLSA provenance in a DSSE envelope, as PyPI's attestations do [PEP 740][SLSA] | Which source and builder produced the bytes |
| Repository metadata | TUF, which addresses rollback, freeze, mix-and-match and malicious mirrors [TUF spec] | Freshness and consistency; a compromised online registry key cannot add a publisher to a namespace with an offline policy |
| Transparency | An append-only log that clients verify and organizations may monitor | No split views |

**Decision D-ECO-16:** Every package version carries a Sigstore signature and SLSA provenance, and its signer must match its namespace's trusted-publisher policy, which the namespace owner signs offline as delegated TUF targets, in the model PEP 480 proposes. Policy changes are logged and notified to the owner, and the lockfile pins each package's signer. Packages under `std::` and `crucible::` and every translator are built by the hermetic builder at SLSA Build level 3 [unverified: level definitions in v1.2] and reproduced bit for bit. *Why:* with online keys alone, TUF does not protect projects from attackers who have compromised the registry, which PEP 458 states and leaves to developer signing in PEP 480 [PEP 458]; reproducible builds let anyone check the registry. *Rejected:* trusting the registry's own record of who may publish (round 1; a compromised registry authorizes itself); signatures without provenance; author-managed GPG keys. (revised in round 2)

Every signature record carries an algorithm id. By phase 2, the TUF root and targets, log checkpoints and registry provenance are dual-signed. The second signature is ML-DSA-87, standardized in FIPS 204 on 13 August 2024 [FIPS 204], or LMS for offline keys.

Long-retention records are re-timestamped before an algorithm retires, and a CNSA 2.0 profile uses only those algorithms [unverified: NSA dates]. A key ceremony gives the TUF root and namespace-policy keys to keyholders at least half of whom are not company employees (D-ECO-22). Air-gapped registries run their own Fulcio and Rekor or organization keys [unverified: Sigstore key-based mode].

### Scanning, advisories and removal

Every publish runs scans: a capability and signer diff shown to dependents, import validation, network targets, secrets, dependency advisories and malware heuristics. A malware finding quarantines the version for human review within 24 h (target). Paid packages' escrowed source is scanned privately before listing, and no code runs at install.

Advisories use OSV 1.9.1 [OSV]. The **correctness advisory** names an operation behavior version, translator or package version whose outputs were wrong. Lockfiles pin every version, so `repo` lists exactly the released designs that used it.

| Action | Effect | Who |
| --- | --- | --- |
| Yank | New resolution skips the version; existing lockfiles keep working and bytes stay downloadable, as in Cargo [cargo yank] | Publisher, as an Act |
| Deprecate | A notice and an optional successor | Publisher, as an Act |
| Quarantine | Download stops; hosts refuse to instantiate; pinned designs fail with `PackageQuarantined` | Security team |
| Legal removal | For a court order, copyright notice or patent notice, after counter-notice where the law provides; a tombstone keeps name, version and hash | Operators, logged |

**Decision D-ECO-17:** Published versions are never deleted by their publishers. Yanking is the only publisher tool. *Why:* released products must rebuild for decades, and a deleted dependency breaks every design that pinned it; npm still allows unpublishing within 72 hours [npm unpublish], but a design can be released within hours of a dependency's publication. *Rejected:* a short unpublish window (breaks early adopters' releases); unrestricted deletion (breaks the rebuild guarantee).

Yanking is not the tool for leaked credentials [cargo yank]; the flow points to revocation or an advisory instead.

### Mirrors, licences and the parts catalog

Mirrors are untrusted transport, since clients verify signatures, TUF metadata and log inclusion. Private registries run the same server; with one configured, resolution denies namespaces not on the organization's allowlist, closing dependency confusion.

Air-gapped sites import signed offline bundles with a log checkpoint. The registry also serves Wasm components in the OCI layout `wkg` reads [wasm-pkg-tools].

Every package declares SPDX expressions for code and for data. The registry checks parsing and file coverage (REUSE style [unverified: version]), reports conflicts and applies organization policy without giving legal advice. Each release manifest lists every package, translator and dataset used, so a release ships its software bill of materials.

Catalog parts differ from packages in volatility. A definition (specifications, geometry, electrical and thermal models, lifecycle, compliance) is a `parts::` package, while offers change hourly and arrive as dated External inputs. A `CatalogSelection` is a pure function over pinned definitions, plus pinned offers when it ranks by price or stock; it re-resolves whenever its arguments change (ELX, ING).

A `parts::<manufacturer>` namespace belongs to the manufacturer once it verifies. Until then the operator curates it, and the manufacturer's definition wins over a community one for new selections.

**Decision D-ECO-18:** A catalog part's definition is a data package under `parts::<manufacturer>::…`, published and signed through the registry. Its offers are not packages: they are signed feeds that a connector turns into dated External inputs. *Why:* definitions must be pinned and reproducible like code, which the registry already does; offers are volatile and must never make a build depend on the network. *Rejected:* putting everything in the registry (hourly versions of price data); keeping catalog definitions outside the registry (a second signing, versioning and pinning system).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Signed first-party index | First-party packages as TUF targets from the hermetic builder | Client refuses unverifiable entries | ECO-O-9 | 1 |
| Public registry and trusted publishing | Namespaces, OIDC publishing, the pipeline | Typed error naming the failed step | ECO-O-9, ECO-O-19 | 2 |
| Namespaces | Prefixed code-host claims, look-alike holds, re-verification | `NamespaceTaken`, `HeldForReview` | ECO-O-9 | 2 |
| Resolution and lockfile | PubGrub; signer and registry pinned | `Unsatisfiable`; `SignerChanged` awaits approval | ECO-O-9 | 0 |
| Compatibility labels | Interface, output and entity-name diffs | Refusal naming the item | ECO-O-10 | 1 |
| Signing, policies and transparency | Sigstore, SLSA, offline namespace policies, TUF, log | Client refuses; monitors alert owners | ECO-O-9 | 1 (first-party), 2 |
| Post-quantum dual signatures | ML-DSA-87 or LMS beside the current algorithm | Single-signed records fail under the CNSA profile | ECO-O-9 | 2 |
| Scanning, advisories, removal | Scans, OSV and correctness advisories, yanks and legal removal | Quarantine; `PackageRemoved` with a fix | ECO-O-19, ECO-O-29 | 2 |
| Private registries and bundles | Deny-by-default namespace map; offline bundles | `NamespaceNotAllowed` | ECO-O-9 | 2 |
| Licence metadata | SPDX, coverage, policy | Invalid expressions refused | ECO-O-31 | 1 |
| Catalog-part definitions | `parts::` packages; offers as External inputs | Stale offers flagged in Proposals (MFG) | ECO-O-16 | 2 |

## Marketplace

The marketplace is the registry's commercial layer, with no second distribution system. Listings open with the public registry in phase 2, and paid packages in phase 3.

| Publisher level | Requirement | Grants |
| --- | --- | --- |
| Account | Verified email and phishing-resistant 2FA | `u_<handle>` |
| Organization | A domain verified by DNS TXT, or a code-host organization by OIDC (prefixed) | A namespace for it |
| Verified publisher | Know-your-business checks with restricted-party screening, a security contact, the publisher agreement | Paid packages; manufacturer-verified catalog parts |
| Certified integration | A passed integration suite | Listing in ordering and quoting flows |

Badges link to the dated record of the checks that ran and never claim quality.

**Decision D-ECO-32:** Verification changes badges, never integrity. All third-party package text (READMEs, docs, description templates, catalog definitions) reaches readers as `ExternalText`, whether or not the publisher is verified; only first-party std and `crucible::` documentation built by the hermetic builder is trusted text. *Why:* verification establishes who published, not that the text is safe to obey, and a compromised publisher account or CI would otherwise gain instruction authority over agents, which AGT grants only to the delegating human, approved role skills and first-party documentation. *Rejected:* trusting verified publishers' text (round 1).

**Decision D-ECO-19:** Paid packages are ordinary registry packages whose download needs an entitlement. The entitlement is a signed, offline-verifiable token, checked by the host before instantiation and never during evaluation. Once a design pins a paid version, it rebuilds forever with that version. *Why:* evaluation must stay deterministic and offline, and a licence server inside a build would break both; designs must not become hostage to a vendor's billing. *Rejected:* runtime licence checks inside Wasm components (network in evaluation, and builds fail when a vendor disappears); a separate commercial store (a second package system).

| Rule | Detail |
| --- | --- |
| Expiry | Blocks new versions and installs only; every paid version stays downloadable for any organization that ever held an entitlement |
| Results | Ordinary CAS objects; a collaborator without an entitlement gets `EntitlementRequired`, never cached, only when an input changes |
| Source | Compiled Wasm components only, with public worlds, manifests and test vectors; escrowed source is scanned privately for licences, secrets and malware before listing |
| Escrow | Source and build recipe with an independent agent under a published beneficiary agreement; if the publisher disappears or stops sales for 12 months, licensees may rebuild for their own use [unverified: enforceability per jurisdiction] |
| Export | A declared `export_classification` (ECCN, EAR99 or not subject, with the basis); screened purchases; comprehensively sanctioned jurisdictions geo-restricted |
| Pricing | Per seat, organization or usage, metered outside evaluation; a cap never stops a pinned design from building |

Suppliers publish catalog-part definitions as signed data packages (D-ECO-18) and offers through a connector. One `offer` record covers price breaks, stock, lead time, minimum quantity, packaging and validity, and a catalog part's key is (manufacturer namespace, manufacturer part number).

Manufacturing partners (machine shops, sheet-metal shops, print services, board fabricators and assemblers) implement `crucible:connect/partner`, with async `request-quote`, `place-order` and `get-status`. A quote request names a release by its signed tag and carries content-addressed Files. It therefore runs only inside a `request_quote` Act of the `release_data` family (D-ECO-28), and orders run inside `order` Acts.

Quotes return as External inputs, and feedback such as "hole too close to bend" arrives as comments anchored through persistent ids. A partner earns "Certified" on a published suite of golden-product release packages, for 12 months.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Verified publishers | Business checks, screening, dated badges | Verification refused, naming the failed check | ECO-O-29 | 2 |
| Third-party text as `ExternalText` | Every publisher's READMEs, docs, templates and definitions | None; text returned by handle | ECO-O-18 | 2 |
| Paid packages, escrow and scanning | Offline entitlements; independent escrow; private scans | `EntitlementRequired`, never cached; listing refused on a finding | ECO-O-20, ECO-O-29 | 3 |
| Supplier offers | One `offer` record as dated External inputs | Stale offers flagged in Proposals | ECO-O-16 | 2 |
| Manufacturing partners | Quotes and orders inside Acts; certification suite | `partner-error` mapped to typed errors | ECO-O-28 | 3 |

## Open-source governance and compliance

### Licence and contributions

**Decision D-ECO-20:** Crucible's code (kernel, language, compiler, Kiln, std, SDKs, WIT packages, registry server and translators) is licensed Apache-2.0 WITH LLVM-exception. Documentation is CC-BY-4.0. Examples and templates are MIT-0, so anyone can copy them into a proprietary design without attribution. Open specifications (the CAS encoding and the repository archive format) are published under a royalty-free patent commitment from the steward [unverified: commitment wording]. *Why:* the toolchain embeds its own code in artifacts users distribute (generated bindings, runtime code in exported FMUs), and the LLVM exception waives Sections 4(a), 4(b) and 4(d) for that case [LLVM exception]; Apache-2.0's patent licence terminates for anyone who sues over the Work [Apache-2.0]; it matches the Rust and Wasm projects Crucible builds on [wasm-pkg-tools]. *Rejected:* MPL-2.0, whose reciprocity covers only edits to existing files while its per-file source obligations land on every embedder, although its Section 5.2 also ends the patent licence of a party that sues [MPL-2.0][MPL FAQ]; dual MIT OR Apache-2.0, because MIT carries no patent grant.

| Dependency licence | Use | Obligation in every distribution |
| --- | --- | --- |
| MIT, Apache-2.0, BSD, ISC, Zlib, Unicode-3.0 | Linked | Notices |
| MPL-2.0 | Linked files | MPL notices and a source offer for each MPL file in native, Wasm, browser and container distributions, as Section 3.2(a) requires [MPL-2.0]; modifications published under MPL-2.0 |
| LGPL, GPL, AGPL | Never linked: external tool, External Op or test oracle | Distributed container images ship their corresponding-source offer |

**Decision D-ECO-21:** Contributions are accepted under the Developer Certificate of Origin 1.1, signed off in each commit, with no CLA and no copyright assignment. Agents never add `Signed-off-by`; every agent-assisted commit carries a mandatory `Assisted-by: <tool, model>` trailer, and the human's `Signed-off-by` certifies their review plus the Linux Foundation's conditions for generated content. Agent-authored diffs over 50 lines run a code-similarity scan against known copyleft corpora, and a match blocks the merge. *Why:* the DCO certifies that the work "was created in whole or in part by me" or builds on suitably licensed work "to the best of my knowledge" [DCO], which a human cannot know of agent output without review and a scan; the Linux Foundation asks contributors to confirm that the tool's terms fit the project licence and that third-party material in the output is licensed and attributed [LF generative AI]. *Rejected:* a CLA with copyright assignment (enables the relicensing that neutral stewardship rules out); agent contributions with only a provenance trailer (round 1; the Apache-2.0 core could absorb GPL-derived code). (revised in round 2)

`ChangeProvenance` is mirrored into the public history. Area teams may require human reimplementation in determinism-critical crates (`detmath`, `kernels`, `anvil-*`), and protected paths such as `oracles/` need human approval.

### Stewardship and decisions

**Decision D-ECO-22:** The founding company stewards the project until a fixed trigger, then transfers the repositories, the open project's trademarks and the registry's namespace authority to a neutral foundation. The trigger is the earliest of the phase 3 gate, the first 12-month period in which at least three other organizations employ active maintainers, and 36 months after the first stable release. The commitment binds from phase 0: the trademarks are assigned in escrow to an independent party that completes the transfer at the trigger, and a key ceremony places the TUF root and namespace-policy keys with keyholders at least half of whom are not company employees. Marketplace ranking and badge rules are published policy, and after transfer the company holds a trademark licence for its hosted services. *Why:* engineering organizations keep product data for decades and need assurance that the kernel and language cannot be relicensed, abandoned or captured; phase gates have no dates, so a gate alone is no deadline. *Rejected:* a foundation at launch (governance overhead before a community exists, and contract section 7.7 fixes company stewardship first); a charter sentence alone (round 1; unenforceable); permanent company stewardship. (revised in round 2)

The company keeps hosted services, marketplace operation, licensed-translator integrations, support and certification delivery. A technical steering committee of 5 to 9 people, at most one third from one employer after transfer, settles cross-team conflicts and governance. Area teams review in their areas, and security, registry-operations and moderation teams handle embargoes, disputes and conduct.

Significant changes go through public RFCs modelled on Rust's, covering motivation, design, oracles, determinism, security, migration and alternatives. A shepherd is assigned within 14 days (target), and a ten-day final comment period precedes a written decision. A feature stabilizes once its oracles pass on every Tier 1 platform.

RFCs are required for new operation families, language changes and editions, new WIT packages, capabilities or contexts, registry policies, and licence, governance or trademark policy. Agents may draft and implement RFCs; only humans approve and vote.

### Releases, editions and support

PLT owns the release train (D-PLT-27): a stable release every 6 weeks and one LTS release a year, supported for 24 months like Wasmtime's LTS [Wasmtime releases]. Contract section 7.7 adds regulated extended support: one LTS line every two years lasts 10 years, with security backports or retired engines run in sandboxes. The registry keeps every package version and binary that a supported line's designs pin.

KLN owns the regulated cloud mode for defence customers, including DFARS 252.204-7012's 72-hour reporting, 90-day image retention and forensic access [DFARS 7012]. ECO assembles the Computer Software Assurance package for medical customers under FDA's final guidance [FDA CSA]. It holds intended use and risk tier per capability, vendor oracle evidence, release impact notes, a supplier quality agreement template and audit rights.

**Decision D-ECO-23:** Ingot uses editions, declared per package in the manifest, as Rust does. Packages of different editions interoperate in one build, editions change only surface syntax, the prelude and lint defaults, and `crucible migrate` applies the fixes automatically. An edition never changes the behavior version of an operation that a lockfile pins. *Why:* Rust's edition model allows incompatible surface changes without splitting the ecosystem, because every edition compiles to the same internal representation [Rust editions]; keeping behavior versions out of editions means a migration can be checked by rebuilding. *Rejected:* versioning the whole language in lockstep (forces every package to migrate at once); no editions (the language could never fix early mistakes).

A migration must leave every golden product's and registry test design's output hashes unchanged (ECO-O-13). Editions are named by year, at most one every three years (target), and ING owns the rules within one.

### Security, export and trademarks

Reports go to a `security@` address, `security.txt` [unverified: RFC 9116 details] or private reporting on the code host. Acknowledgment comes within 2 business days (target), and the 90-day default embargo shortens under active exploitation. Advisories use OSV with CVSS v4 [OSV], and a paid bounty starts in phase 2.

Under the EU Cyber Resilience Act the company is the manufacturer of its commercial distributions, and the foundation becomes an open-source steward under Article 24 [CRA]. An actively exploited vulnerability triggers an early warning within 24 hours and a notification within 72 hours on ENISA's single platform, whatever the embargo [CRA].

Correctness defects that could make a product unsafe get the same urgency:

| Severity | Meaning | Response |
| --- | --- | --- |
| C1 | A `SignOff` result is non-conservative, or an export moves manufactured geometry beyond tolerance | Advisory within 72 hours of confirmation (target); affected-release owners notified through `repo` |
| C2 | An `Interactive` result or non-critical export is wrong beyond its bound | Advisory with the next stable release |
| C3 | Metadata or presentation only | Changelog entry |

**Decision D-ECO-29:** The steward classifies each distributable (open-source code, commercial binaries, the hosted service, first-party packages) under the EAR and the EU dual-use regime and publishes classification statements for customers. If any distributable uses non-standard cryptography, its publicly available source is notified to BIS and the NSA as 15 CFR 742.15(b) requires [15 CFR 742.15]. The registry refuses any package that carries `export_controlled` labels, and paid packages must declare `export_classification`. *Why:* commercial binaries and the hosted service contain cryptography, customers need statements for their own compliance, and a public registry must never become an export channel. *Rejected:* deferring export control until paid packages open (round 1 open question).

Contract section 13.1 makes names a phase 0 gate. Flux is renamed, because Siemens sells Simcenter Flux, electromagnetic simulation software for motors, sensors and power devices [Simcenter Flux], and flux.ai is a PCB design tool [Flux AI].

"Crucible" gets full clearance in the US, EU, UK, China and Japan for classes 9 and 42, assuming Atlassian's mark persists. Atlassian still lists Crucible in its trademark chart [Atlassian trademarks], although sales of its product ended in 2025 [Atlassian Crucible]. Names enter `OpKey`s, lockfiles and WIT packages, so frozen names precede the first frozen behavior version and `crucible:` package.

The trademark policy allows referring to and teaching the project and "for Crucible" or "works with Crucible" without implying official status. "Crucible-compatible" needs the published conformance suite, modified distributions need another name ("based on Crucible" is fine), and `std`, `crucible`, `core` and the logos are reserved.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Licence policy | Dependency allow-list; MPL and GPL source offers | A violating distribution is not released | ECO-O-31 | 0 |
| Contribution checks | Human DCO, `Assisted-by`, similarity scan | Merge blocked, naming the rule | ECO-O-30 | 0 |
| Binding stewardship | Trigger with backstop; trademark escrow; key ceremony | Root metadata below the keyholder threshold fails verification | ECO-O-9 | 0 |
| Regulated support artifacts | Pinned versions kept per supported line; CSA package per LTS | A line without its CSA package is not promoted | ECO-O-22 | 2 |
| Disclosure and CRA reporting | Embargoes, advisories, 24 h and 72 h reports | A missed deadline is recorded as an incident | ECO-O-29 | 1 |
| Export classification | Statements per distributable; registry refusals | `ExportControlled` or `ClassificationMissing` at publish | ECO-O-29 | 1 |
| Name clearance | Names frozen before behavior versions and WIT packages | Freeze refused while names are uncleared | ECO-O-6 | 0 |

## Documentation and community

AGT specifies agent-facing references (D-AGT-23) and UIX tutorials verified by scripted solutions; ECO specifies the system around them.

**Decision D-ECO-24:** Documentation is organized by the four Diátaxis types: tutorials, how-to guides, reference and explanation [Diátaxis]. Reference is generated, and every code sample in every type is a tested example. *Why:* the four types serve four distinct needs [Diátaxis], so each page does one job; generated reference cannot drift from the code. *Rejected:* a single manual (mixes learning and lookup); a wiki (unversioned, untested).

Tutorials follow each golden product from sketch to release, and how-to guides cover tasks such as running a private registry. Reference covers methods, std, worlds, error codes, manifest keys, the CLI and each catalog format, and explanation covers concepts.

Every code block builds with its Checks passing, and every public item has a doc comment, an example and units. Pages name their versions and ship with the desktop app for offline use. The registry generates reference documentation for every package, and a failing `examples::` package (MIT-0) blocks a std release.

The community has a forum, chat, an issue tracker and monthly office hours per area team, under the Contributor Covenant [unverified: version], and a yearly conference from phase 3. Certification is graded by oracles. Associate and Professional candidates pass practicals with hidden Checks in any editor, Package Developers publish packages that pass hidden test vectors, and software earns "Crucible-compatible" through conformance suites.

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
| Semantic PMI; mates | GD&T on faces (presentation-only where the source has no semantics, flagged); mates where exposed, else fixed placements | AP242 or licensed readers [unverified per format] | 2; 3 |
| Drawings; PDM history | PDF and DXF Assets; released revisions without feature history | Files; PLM connectors (D-ECO-30) | 1; 4 |
| NC programs | Assets of kind `Program` linked to part revision and machine, verified by MFG's `verify_nc`, never converted to workingsteps, with the same approval and transfer path as generated programs | Bulk import | 2 |
| Tool libraries, posts, setup sheets | Tool Assemblies through the tool-data readers; posts and sheets as Assets | Bulk import | 2 |
| ECAD designs and libraries | Schematics, boards, symbols, footprints and parameters; library parts become catalog parts with internal numbers (ELX) | Own EAGLE XML reader; KiCad for the rest (D-ECO-31) | 3 |
| Boards without schematics | Layout, netlist and BOM | IPC-2581 and ODB++ read | 3 |

**Decision D-ECO-31:** Proprietary ECAD designs migrate through KiCad's importers, run as an external tool in a pinned container, followed by Crucible's own KiCad reader; EAGLE XML also gets an own reader. *Why:* Autodesk ended EAGLE sales and support on 7 June 2026 [EAGLE], and KiCad 9 already imports EAGLE 6.x XML, CADSTAR, EasyEDA, Altium SchDoc and PcbDoc, P-CAD and Fabmaster [KiCad 9 docs]; KiCad is GPL-3.0 or later [KiCad licences], so it runs only out of process with a source offer for its image (contract section 7.7). *Rejected:* licensed translators per ECAD format (most do not exist); own readers for every proprietary ECAD format (large, undocumented formats).

**Decision D-ECO-25:** Crucible does not import parametric feature history from proprietary systems. It imports geometry, structure, semantic PMI and metadata, and it offers reconstruction of design intent as a reviewed Proposal. *Why:* proprietary feature definitions are vendor- and version-specific, their exact semantics are undocumented, and replaying them without the original kernel gives different geometry; a history that rebuilds differently is worse than no history, because it fails silently. Reconstruction against the imported geometry, by contrast, can be checked. *Rejected:* translating feature trees through licensed SDKs (fragile per version, unverifiable); macro-recording replay (same problem).

Configurations, design tables, equations and sketches stay behind as live data; their results arrive as geometry.

### Reconstruction and tooling

Reconstruction, run by an agent role and delivered as a Proposal, has four steps:

1. **Recognize** extrusions, holes with `HoleSpec`, fillets, chamfers, patterns, shells and drafts: rules for prismatic parts, learned segmentation for the rest. BRepNet's convolutions over oriented coedges inform the model [BRepNet]. Shipped models train only on Crucible's procedural corpus and data with verified commercial licences (D-AGT-22). The Fusion 360 Gallery dataset allows only non-commercial research [Fusion 360 Gallery licence], so it serves only non-shipping benchmarks.
2. **Generate** Ingot features with std features and the imported PMI as constraints.
3. **Verify** against the import: Hausdorff distance under 1 µm (target), equal topology in normal form, every PMI item re-attached through a `Query`.
4. **Fall back** to imported geometry for regions that fail, joined by direct-edit operations and listed.

The target: 9 of 11 NIST CTC and FTC parts and 80% of a held-out prismatic set rebuild with all PMI by the phase 3 gate.

| Source or tool | Approach | Phase |
| --- | --- | --- |
| OpenSCAD [unverified: licence]; spreadsheet design tables | Translator for CSG, extrusions and modules; tables become parameter files and variant sets | 2 |
| Zoo KCL [KCL docs]; CadQuery and build123d [unverified: licences] | KCL translated, pipelines to `\|>`; Python sources run in a pinned container whose operation trace becomes Ingot | 3 |
| Onshape FeatureScript [unverified: terms], shipped in ABC [ABC] | Translator for std calls, units and sketches; unknown calls become `Untranslated` stubs | 4 |
| `crucible import scan` and bulk import | Inventory of formats, broken references and duplicates by geometry hash; one repository per product, resumable | 2 |
| Subordinate mode | The enterprise PLM stays the system of record while Crucible releases into it (D-ECO-30) | 2 |
| Parallel run, round-trip bridge, library migration | Re-import incumbent releases and report differences; AP242 with persistent ids back; standard parts to packages | 3 |

Translators run in the tool context and must match the original's STEP export within tolerance. Migration never modifies source data, and every converted model keeps its source File by hash.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| MCAD migration | Geometry, structure, PMI, metadata, drawings | Per-file report; nothing dropped silently | ECO-O-1, ECO-O-17 | 1 to 4 per row |
| Manufacturing-data migration | Programs, tool libraries, posts and setup sheets | Unverified programs never reach a transfer Act (MFG) | ECO-O-17 | 2 |
| ECAD migration | EAGLE reader; KiCad as an external tool; legacy board read | `Untranslated { construct }` per file | ECO-O-25 | 3 |
| Reconstruction and source translators | Recognize, generate, verify, fall back; match the original's export | Unverified regions stay imported and are reported | ECO-O-21 | 2 to 4 per row |
| Inventory, bulk import, subordinate mode | Scan, convert, coexist | Per-file report; resumable | ECO-O-17, ECO-O-27 | 2 |

## State of the art

Figures are targets.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| STEP AP242 translation | Schema-generated Part 21 plus CAx-IF practices [CAx-IF GVP][CAx-IF 58J] | Commercial translators in CAx-IF rounds; Open CASCADE 8.0.1 [OCCT releases] | Three-layer Rust translator (D-ECO-3) in every round (D-ECO-5) | Round results; volume and area within 0.05%; zero SFA errors; PMI statistics equal on every NIST case |
| STEP read throughput | Streaming Part 21, lazy resolution | Open CASCADE | Streaming, parallel translation, deterministic merge | A 1 GB file at least 2× Open CASCADE on the reference laptop; browser within 3× of native |
| Proprietary CAD import | Vendor SDK access | CAD Exchanger, HOOPS Exchange, Datakit [CAD Exchanger formats][HOOPS Exchange][Datakit] | Licensed, out of process, pinned (D-ECO-2) | Qualification on NIST and held-out native models |
| Validation and repair | Validation properties as receiver oracles [CAx-IF GVP] | Commercial healing tools [unverified: names] | `anvil::heal` with bounds per entity | Healed entities bounded; re-export within production thresholds |
| Sandboxed extensions | Component Model; WASI 0.3 async for effectful worlds [WASI 0.3] | Wasmtime [WASI 0.3]; jco [jco] | Synchronous evaluation worlds (D-ECO-9); one browser runtime (D-ECO-10) | Every first-party world on Wasmtime, WebKit and three browser engines; ≤ 1.6× native Rust in Wasmtime, ≤ 2.5× in browsers |
| Deterministic execution | Injected metering [wasm-instrument][finite-wasm]; Wasm 3.0 deterministic profile [Wasm 3.0] | Wasmtime fuel, native only [Wasmtime determinism] | PLT's determinizer at publish (D-ECO-8) | Identical outputs and traps on 10⁴ vectors per Wasm component |
| Supply-chain integrity | Sigstore [Sigstore]; SLSA v1.2 [SLSA]; PEP 740 [PEP 740]; TUF with offline delegations [TUF spec][PEP 458] | PyPI attestations; npm and crates.io trusted publishing [npm security plan][crates.io update 2025-07] | All of these, plus offline namespace policies and pinned signers (D-ECO-16) | Every entry verifiable offline; an online key cannot add a publisher; first-party packages reproduced |
| Resolution and SemVer | PubGrub [PubGrub]; Rustdoc-JSON linting [cargo-semver-checks] | uv and Cargo [unverified: algorithms]; cargo-semver-checks | PubGrub with typed explanations; interface, output and name diffs (D-ECO-14) | Full graph under 1 s; seeded breaks all caught, no false refusals |
| Vulnerability data | OSV 1.9.1 [OSV] | OSV.dev, RustSec, GitHub Advisory Database | OSV plus correctness advisories | Advisory-to-lockfile match under 1 h |
| Events and webhooks | CloudEvents 1.0 [CloudEvents]; Standard Webhooks [Standard Webhooks spec] | SaaS webhook platforms [unverified] | Both, Ed25519 by default (D-ECO-12) | Reference verifiers; delivery under fault injection |
| Board exchange and ECAD migration | IDX V6 [prostep IDX]; KiCad importers [KiCad 9 docs] | KiCad 9 [KiCad 9.0] | IDF and IDX readers; KiCad as an external tool (D-ECO-31) | Netlist equality and empty Gerber XOR against the source tool |
| Feature recognition | B-rep message passing [BRepNet]; rules for prismatic parts | Commercial recognizers [unverified: names] | Rules plus segmentation trained on licensed data, verified by rebuild | 9 of 11 NIST parts rebuilt with PMI by the phase 3 gate |
| Documentation | Diátaxis [Diátaxis]; tested reference | docs.rs with doc tests [unverified as a benchmark] | Diátaxis, tested and offline (D-ECO-24) | Coverage 100%; every example builds |

Deviations, with reasons:

- Licensed translators run outside evaluation: determinism and portability.
- Wasm components are CPU-only: no deterministic, portable GPU interface exists for sandboxed code.
- No 64-bit memories, and HDF5 formats wrap the C library: maturity.

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Every Tier 1 target | Translators differing per platform | Determinized translators; byte-identical exports (ECO-O-4) |
| Windows, macOS, Linux | Licensed SDKs ship for some OS and architecture pairs only [CAD Exchanger formats] | Run where the vendor ships, else on a server; the External input is the same everywhere |
| Windows ARM64 | Wasmtime Tier 3 [Wasmtime tiers]; vendor SDKs [unverified] | Third-party Wasm components already out of process (D-ECO-26); translators on a server |
| Browsers | No native Component Model; no local tool or connector context; files via pickers | One Wasm component runtime (D-ECO-10); tools and connectors on the server; imports upload bytes to CAS first, so Asset hashes match desktop imports |
| iPadOS (Tier 2) | No JIT; guidelines 2.5.2, 3.2.2(i), 4.2.3(ii) and 4.7 [App Review] | WebKit, bundled std and packages only as design dependencies (see Isolation and platforms) |
| Android (Tier 2) | Wasmtime Tier 3 [Wasmtime tiers]; Play's downloaded-code rule [Google Play DNA] | No world imports Android APIs; PLT funds upstream coverage |
| Air-gapped installs | No Sigstore, public registry or licence servers | Offline bundles with a private signing root; offline activation where vendors offer it [unverified per vendor]; offline entitlements |
| Text inside files | Encodings and normalization differ | Decode per the declared encoding, normalize names to NFC through the platform layer, keep original bytes |

## Interfaces with other subsystems

### What ECO requires

| From | Requirement |
| --- | --- |
| ANV | Builders with healing; certified mass properties; D-ANV-31, `import_map`, the normal form and `exchange_form`; tessellation |
| MEC | The GD&T model and its AP242 mapping; `ShapeAspect`; joints; composites; design-time flags for semantic controls on facet faces |
| FLX, COV | Field encodings for AP209, CGNS, Exodus, VTK, BDF, Abaqus and OpenFOAM; the FMI and SSP runtime (D-FLX-30); solver and constitutive world semantics |
| ELX | The board, netlist and library models; IDX, IPC-2581, ODB++ and KiCad semantics; `CatalogSelection`; SysML v2 and ReqIF mappings |
| MFG | The factory handoff; machine, tool and toolpath models; `verify_nc`; offer usage; partner flows |
| ING | Module system, manifest language keys, lockfile `[language]`, editions, wrapper conventions, the SemVer row for entity-name changes |
| KLN | Leaf inputs; Ops keyed by determinized hashes; event types and sequence numbers; data-package records; the system-of-record policy; the regulated cloud mode |
| AGT | Catalog entries above; Act classes and the `release_data` family; `ExternalText` and instruction authority; render rules for untrusted Bodies; audit; MCP subscriptions |
| PLT | The determinizer and overhead table; Wasmtime LTS and 7-day security releases; the OS sandbox for workers; the browser runtime host; offline bundles; NFC normalization |
| UIX | Rendering of reports, grants, package pages and marketplace flows; panel chrome showing package identity |

### What ECO provides

| To | Provides |
| --- | --- |
| All tabs | The standards catalog and `TranslationReport`; `crucible:` WIT packages, contexts, capabilities and limits; the registry; event delivery (D-ECO-12) |
| ANV, FLX | `crucible:ops`, generated from their catalogs |
| KLN | Determinized hashes for keys; webhook delivery for its events; enterprise connectors; the watermark transform |
| AGT | Signing for `std::agents` and `std::explore`; licence metadata; `release_data` members for archive, mirror, bundles, partners and connectors |
| ELX, MFG | Board, manufacturing and tool-data readers and writers; `parts::` publishing and the offer schema; ECAD and NC migration |
| FLX, COV | Hosting for solver and constitutive Wasm components; FMU packaging with FMI-LS-WASM |
| UIX; PLT | Package metadata, capability descriptions and badges; worlds to enforce, declared memory limits, the browser Wasm component description, font packages for design text |
| Everyone outside | SDKs, C ABI, CLI, webhooks, and the archive and CAS encoding specifications |

## Oracles

ECO's oracles live in `oracles/eco/`, readable but not writable by agents; held-out corpora stay outside the agent-readable tree.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ECO-O-1 | STEP readers: declared validation properties against Anvil's values on every corpus file | All within production thresholds; 95% within 0.05% on volume and area (target) |
| ECO-O-2 | Semantic PMI export and import on the NIST CTC, FTC, STC and HTC cases | Every item equal in type, value, tolerance, datums and targets; facet-face controls presentation-only |
| ECO-O-3 | Exported files: generated EXPRESS rules, NIST SFA, XSD and consortium validators | Zero errors |
| ECO-O-4 | Export determinism: every golden product in every format on every Tier 1 platform, browser included | Byte-identical Files |
| ECO-O-5 | Readers under structure-aware and grammar-based fuzzing | No panic, no allocation beyond limits, termination within fuel; 10⁹ executions per release without a new crash (target) |
| ECO-O-6 | Engine identity: 10⁴ vectors per first-party Wasm component on Wasmtime (x86-64, ARM64), WebKit, Pulley, V8 and SpiderMonkey, rerun before any engine upgrade | Identical outputs, host-call sequences and trap points |
| ECO-O-7 | Publish-time and build-time determinization with one determinizer version | Byte-identical binaries; forbidden features refused with offsets |
| ECO-O-8 | Capabilities and isolation: red-team Wasm components reaching forbidden imports, undeclared hosts, foreign directories, secrets, labelled reads plus egress, worker or browser-sandbox credentials | Every attempt refused, typed and audited; workers hold no tokens, handles or keys |
| ECO-O-9 | Registry integrity: altered bytes, rollback, freeze, mix-and-match, split views, forged provenance, an online key adding a publisher, signer changes, lapsed domains, unlisted namespaces, a root below the keyholder threshold | Every case detected; rebuilt first-party hashes equal published ones |
| ECO-O-10 | Compatibility gates: seeded breaks, output changes and entity renames in minors and patches | Breaks refused; changes labelled |
| ECO-O-11 | SDKs and C ABI: AGT golden transcripts through every SDK; ABI symbol diff | Byte-identical canonical JSON; no symbol removed in a major |
| ECO-O-12 | Exit: an independent reader in another language, from the specifications alone, reads golden-product archives | Same Changes, Body measurements within bounds, same BOM |
| ECO-O-13 | Edition migration on every golden product and registry test design | Identical output hashes |
| ECO-O-14 | Events and webhooks under outages, slow and failing receivers, duplicates and SSRF probes | At least once, deduplicated, ordered per repository, signatures verified, probes refused |
| ECO-O-15 | Licensed translator qualification per pinned version | Record reproduces; thresholds met or the version flagged |
| ECO-O-16 | Every catalog row on its conformance suite (3MF, Reference FMUs, SSP, IFC, KiCad, Gerber re-reading, tool data within 1 µm) | Every row at or below the current phase passes |
| ECO-O-17 | Nothing lost: source entities counted by kind against report entries, per corpus and bulk-import file | Every entity accounted for |
| ECO-O-18 | Untrusted content: injections in names, PMI, notes, metadata, package READMEs, embossed text and textures (shared with AGT) | No string reaches an identifier, error text or agent context except as `ExternalText`; derived Bodies carry `data_untrusted` |
| ECO-O-19 | `crucible add` and `crucible update` traced | No package code runs |
| ECO-O-20 | Paid packages offline with valid, expired and revoked entitlements | Pinned designs always rebuild; unentitled new versions blocked |
| ECO-O-21 | Reconstruction and source translation on NIST parts and a held-out prismatic set | 9 of 11 NIST parts and 80% of the set within 1 µm with all PMI by the phase 3 gate (target) |
| ECO-O-22 | Re-export of archived golden-product releases from every earlier stable and LTS release | Byte-identical to the archived Files |
| ECO-O-23 | Part 21 layer: read then write every corpus file; dictionary-driven against generated access | Every instance reproduced; equal values |
| ECO-O-24 | Round trips in normal form: self round trips and Open CASCADE differential reads | The suites' pass lines; every disagreement triaged |
| ECO-O-25 | Board writers and ECAD migration on open EAGLE, Altium and KiCad designs and Crucible boards | Netlists equal the source tool's export; Gerber XOR empty; ODB++ matches KiCad's writer |
| ECO-O-26 | Board exchange: KiCad's IDF and STEP exports of an open board | Outline, holes, keep-outs, heights and reference designators equal the source |
| ECO-O-27 | Enterprise connectors against a mock ERP and mock PLM, replaying every event | Idempotent; field ownership respected; release and approval round trip with unchanged digests |
| ECO-O-28 | Every exit path with and without an approved `release_data` plan | Nothing leaves without one; label, screening and authorization failures refuse the commit |
| ECO-O-29 | Compliance: labelled or unclassified packages, screened parties, escrow scans, a simulated exploited vulnerability | Refused or flagged; CRA reports drafted within 24 h and 72 h in the drill |
| ECO-O-30 | Contributions without a human `Signed-off-by`, with an agent's, without `Assisted-by`, or with seeded copyleft snippets | Every case blocks the merge |
| ECO-O-31 | Licence policy on every distribution | No disallowed linked licence; every notice and source offer present |
| ECO-O-32 | Documentation and certification | Every example builds; coverage 100%; graders agree with reference solutions |
| ECO-O-33 | Watermarks for several recipients | Each file traces to its release and recipient by recomputation |

## Phasing

| Phase | ECO contribution to the gate |
| --- | --- |
| 0 | ECO-O-6 and ECO-O-7 green in the determinism suite; `crucible:` packages at 0.x, none frozen before names clear; STEP layer 1; licence and contribution checks; the charter's binding stewardship trigger, key ceremony and trademark clearance commissioned; Rust SDK |
| 1 | GP1: AP242 with geometry, structure, validation properties and semantic PMI passing ECO-O-1 to ECO-O-4, in a release bundle. GP2: 3MF with beam lattice passing consortium validation. Also AP203 and AP214 read, STL, the signed first-party index, the first CAx-IF round, the Python SDK, CLI, events, archive and docs. Deferred per contract section 13.2: the public registry and trusted publishing |
| 2 | GP3 and GP4 exchanged with an external CAD system by AP242 round trip with persistent ids; GP3's legacy programs and tool libraries imported for MFG. Also licensed translators, board exchange, the public registry, enterprise connectors, the TypeScript SDK, the C ABI and dual signatures |
| 3 | GP5's board fabricated and assembled from Crucible's Gerber X2, XNC, IPC-2581C or ODB++ and placement outputs; FMI import; ECAD migration; paid packages and certified partners |
| 4 | GP6 FE and CFD models exchanged with an external solver; FMU export and SSP (contract section 13.4); robot descriptions; IDX change proposals |
| 5 and later | GP8 round-tripped through IFC 4.3; AP239 and AP233; GP14's IFC export in phase 7 |

## Open questions

1. **Translator vendor.** CAD Exchanger, HOOPS Exchange or Datakit first? The deciding terms (server use, External inputs that unlicensed collaborators rebuild from, ARM64 and Linux builds, offline activation) are not public [unverified].
2. **CAx-IF terms.** What does membership cost, and may round files enter the protected corpus?
3. **EXPRESS sources and `espr`.** May the AP242 schemas be used for code generation [unverified]? Adopt and maintain `espr`, silent since September 2024 [espr crates.io], or write a generator?
4. **OSV ecosystem.** Will OSV accept a `Crucible` ecosystem, and where do correctness advisories go?
5. **Foundation.** A new foundation or an umbrella project? It decides trademark holding, registry operation and funding.
6. **Marketplace terms.** Fees, refunds, disputes and tax.
7. **ODB++ terms.** Siemens' current terms, checked once before the phase 3 writer ships.
8. **iPadOS.** The phase 3 WebKit spike and App Review's answer on downloaded Wasm components.
9. **CVE identifiers.** Become a numbering authority or use an existing one?
10. **Test corpora.** May the ABC models be used internally, and derived measurements published?
11. **Component Model.** When do the binary encoding reach 1.0 and all engines support 64-bit memories?
12. **Findings declined in part.**
    - R4-29: IDF read and STEP board import arrive on an early 1.x train in phase 2, since contract section 13.2 limits phase 1 to what GP1 and GP2 need.
    - R4-09, R4-10: migrated NC programs and the tool-data readers arrive in phase 2 with CAM, which contract section 13.2 defers.
    - R5-25: no foundation at phase 0, since contract section 7.7 fixes company stewardship until a trigger. The 36-month backstop, trademark escrow and key ceremony make the trigger binding.

## Contract change requests

- **CCR-ECO-8. Third-party Wasm components out of process everywhere.** Section 7.4 sends third-party evaluation Wasm components out of process only where Wasmtime is below Tier 2. Replace it with: *only first-party Wasm components from the hermetic builder run in the engine process; every third-party Wasm component runs in a sandboxed worker on every target, per (tenant, label scope) on servers.* *Reason:* the engine process holds tokens, repositories and signing keys, and Wasmtime's 2026 advisories show the sandbox alone is not enough (D-ECO-26, R5-09).
- **CCR-ECO-9. No per-component JavaScript in browsers.** Section 7.4 says browsers run "registry-built bundles". Replace it with: *browsers instantiate determinized core modules through one first-party Wasm component runtime, and third-party Wasm components run in a cross-origin sandboxed worker.* *Reason:* generated glue would run with the engine worker's authority (D-ECO-10, R5-12).

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
