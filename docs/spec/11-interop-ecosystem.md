# Interoperability and ecosystem (ECO)

Crucible reads and writes the open standards of every engineering domain through sandboxed, deterministic translators, and it reaches proprietary formats only through licensed translators whose results are pinned like any other dependency. Everything anyone adds to Crucible, the core team included, ships through one signed package registry as Ingot packages or Wasm components that behave identically on every platform, including the browser. An open-source core, a neutral governance path and open formats guarantee that no design and no extension is ever trapped.

## Scope and terms

ECO owns five things:

1. **Translation.** The `io/` translators, the translation framework, the standards catalog and the translator quality program.
2. **The Wasm component contract.** Worlds, contexts, capabilities, the determinism contract, sandbox limits, versioning and the determinizer that makes Wasm components portable.
3. **Distribution.** The package registry, publishing of the parts catalog, and the marketplace.
4. **Developer surfaces around the `api`.** SDK packaging, the C ABI, the CLI shape, events and webhooks. The method catalog itself belongs to the AGT tab.
5. **Stewardship.** Licensing, governance, security disclosure, trademarks, documentation, community, certification and migration from incumbent tools.

ECO does not own the meaning of domain data. MEC owns the semantic tolerancing model, ELX owns electrical semantics, MFG owns toolpaths and machine code, FLX owns solver and co-simulation semantics, and AGT owns the `api` catalog. ECO supplies the shared machinery, decides which formats exist and at what fidelity, and runs the oracles that prove each translator works.

This tab adds the following plain names. Each relates to the core types as stated.

| Term | Meaning | Relation to core types |
| --- | --- | --- |
| Translator | A reader or writer for one format family | A Wasm component (open formats) or an external tool (licensed formats). Produces or consumes `Body`, `Part`, `Assembly`, `Field` and `Material`. |
| File | A plain value: name, media type and SHA-256 of bytes held in CAS | The only type a translator reads or writes besides the core types |
| Asset | A File stored in the design repository and referenced from Ingot by path | Its hash is pinned in the lockfile |
| Translation report | A typed record of what happened to every source entity during a read or write | Attached to the result; Checks can read it |
| Fidelity level | One of five levels: visual, geometry, structure, semantics, identity | Declared per format and direction in the catalog |
| External input | Signed, content-addressed data produced outside evaluation, such as a licensed translation, a supplier offer, a machine reading or an external solver run | A CAS object pinned in the lockfile; Kiln treats it as a leaf input. The contract uses "snapshot" for review renders, so this tab never calls pinned data a snapshot (CCR-ECO-1). |
| External tool | A native program run out of process by a tool runner | Its results enter builds only as External inputs |
| World | A WIT world: the complete import and export contract of a Wasm component | Fixes what the Wasm component may call |
| Context | Where a Wasm component runs: evaluation, panel, tool or connector | Fixes which capabilities a world may import |
| Capability | A host interface that a Wasm component imports | Granted per context, per install and by organization policy |
| Fuel | A deterministic unit of computation, charged by code injected at publish time | Budgets; running out is a deterministic, cacheable error |
| Determinized Wasm component | The canonical, instrumented form of a Wasm component that every host executes | Its SHA-256 enters the `Op` cache key |
| Publisher | A verified identity that owns a namespace in the registry | Signs packages and catalog data |
| Entitlement | A signed, offline-verifiable right to use a paid package version | Checked before instantiation, never during evaluation |

Three rules run through the whole tab:

1. The network never reaches evaluation; External inputs do.
2. Nothing is lost silently; every loss and approximation is reported with a bound.
3. Every translator, package and policy has an oracle that agents cannot edit.

## Translation architecture

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

| Function | Contract | Failure behavior | Phase |
| --- | --- | --- | --- |
| `read(path, options) -> Imported` | `path` names an Asset whose SHA-256 is pinned in the lockfile. Returns `Imported { assembly, parts, bodies, report, source }`, where `source` holds the file header (originating system, schema, units, author fields). | Typed `ImportError` (unreadable, unsupported schema, missing units, missing External input), each with a fix | 1 |
| `write(model, format, options) -> File` | Accepts a `Body`, `Part`, `Assembly` or `Field` plus format options. Returns a `File` in CAS with its media type. | `ExportError` listing every construct the format cannot carry; nothing is dropped unless the options say `lossy: allow` | 1 |
| `probe(path) -> FormatInfo` | Identifies format, schema and edition from the first 4 KiB | `Unknown` with the closest matches | 1 |

`Imported` is a plain record, not a new geometry type; its members are core types. `File` is a plain value: name, media type and the SHA-256 of bytes held in CAS.

Kiln caches the parse under the Asset's hash, the options and the translator version, so an unchanged file is parsed once, not on every rebuild.

### Where translators run

Translators run in one of three places. The place depends only on the format's license and on whether the data is live.

| Source | Mechanism | Context | How the result enters a build |
| --- | --- | --- | --- |
| Open formats (Build or Wrap in the catalog) | A Wasm component implementing the `crucible:io` world `importer` or `exporter` | Evaluation | Directly, as a cached `Op` output |
| Licensed formats (native CAD, Parasolid, ACIS; JT at first) | An external tool: a native program built on the vendor SDK, declared by an external-tool manifest and run in PLT's process sandbox. It writes the open CAS encoding through the open-source encoder crate. | Tool | As an External input pinned in the lockfile |
| Live sources (machines, supplier offers, PLM systems) | A connector Wasm component | Connector | As an External input pinned in the lockfile |

**Decision D-ECO-2:** Licensed translators never run inside evaluation. They run as external tools, and their output enters builds only as External inputs, content-addressed in CAS and pinned in the lockfile. *Why:* vendor SDKs are native, closed and not bit-reproducible across platforms or releases; pinning their output keeps every build deterministic and lets anyone rebuild the design without the license. *Rejected:* calling vendor SDKs during evaluation (breaks determinism and cannot run in the browser); compiling vendor SDKs to Wasm (no vendor offers this under its published terms [unverified], and closed code cannot be audited for determinism).

An External input is stored in the CAS encoding: the canonical, versioned serialization of `Body`, `Part`, `Assembly`, `Field`, `Material`, PMI and `HistoryRecord`s that Kiln already uses for CAS. ECO publishes this encoding as an open specification. The external tool therefore walks the vendor SDK's object model and emits Crucible's own data, with no second neutral format in between.

This mechanism and COV's external tools (D-COV-12) are one mechanism with two recording modes. A tool anyone can re-run, such as an open-source solver in a pinned container, runs as a recorded external `Op` on Linux workers and is re-executed on demand.

A tool that needs a license some builders lack has its output pinned as an External input, so every builder can rebuild without the license. The tool manifest declares which mode applies.

When a build needs an External input that the lockfile lacks, evaluation stops with `ExternalInputMissing { asset, translator, options }`. The fix is explicit: `crucible import assets/gearbox.CATProduct`, or one click in the UI, which runs the tool and records the result in a Proposal.

Upgrading the translator re-runs it and produces a lockfile diff. The Proposal then shows the geometry overlay and the change in validation properties, so a translator upgrade is reviewed like any other change.

[[DIAGRAM: Translation flow. Left column, three sources: "Asset in repo (open format)", "Asset in repo (licensed format)", "Live source (machine, supplier, PLM)". Middle: "Importer Wasm component (evaluation context)" fed by the first; "External tool on vendor SDK (tool context, PLT process sandbox)" fed by the second; "Connector Wasm component (connector context)" fed by the third. The last two each have an arrow to "External input in CAS, pinned in lockfile". Right: "Kiln Op: read(...)" receives arrows from the importer and from the External input box, and outputs "Imported: Assembly, Parts, Bodies, PMI + TranslationReport". A dashed arrow labeled "never at evaluation time" separates the tool and connector contexts from Kiln.]]

### Translation report

Every read and write returns a `TranslationReport`. Checks can read it, and the UI renders it beside the model.

| Field | Content |
| --- | --- |
| `entries` | One entry per source entity: source id (such as `#1234 ADVANCED_FACE`), outcome and target `EntityId` |
| Outcome | `exact`, `approximated(ErrorBound)`, `healed(ErrorBound)`, `merged(into)`, `dropped(reason)` or `unsupported(construct)`; healing steps are listed in `diagnostics` |
| `statistics` | Counts by category in the style of CAx-IF statistics: solids, shells, faces, semantic PMI by type, saved views, instances |
| `validation` | Each validation property declared in the file beside the value Anvil computes, with the deviation and a verdict |
| `units` | Source units and the conversion applied |
| `max_deviation` | The largest geometric deviation introduced, as a `Length` |
| `lost` | The dropped and unsupported entries, for quick Checks |
| `diagnostics` | Typed errors and warnings, each with a fix |

Five rules govern failure:

1. Nothing is dropped silently. Every source entity appears in `entries`.
2. Recoverable damage does not abort a read. A malformed STEP instance is skipped and reported; `strict: true` fails on the first error instead.
3. Healing is explicit. Sewing, gap closing and orientation repair are Anvil operations, recorded as `healed` with their `ErrorBound`; `heal: none` disables them.
4. Validation-property mismatches beyond the production thresholds of the CAx-IF recommended practice raise a warning-severity Check that the design can promote to an error.
5. A writer refuses to drop data. It returns `ExportError` listing what the target format cannot carry, unless the caller passes `lossy: allow`, in which case the losses are listed in the report.

### Units and axes

Formats that declare units are converted to SI, and the factor is recorded. Formats without units, such as STL, OBJ and PLY, require a `units:` argument. Omitting it is a compile error, `MissingUnits`, whose fix lists the bounding box in millimetres, inches and metres so the person can see which reading is plausible.

Axis conventions differ: glTF is Y-up in metres [unverified: not re-checked against the glTF 2.0 text], and OpenUSD declares its up axis and metres per unit in stage metadata [unverified]. Crucible applies the conversion as an explicit transform and records it in the report.

### Identity across round trips

An imported entity's `EntityId` uses the import `Op` as its operation and a role taken from the source. The role is the source's persistent identifier when the format has one: AP242 persistent IDs, which the CAx-IF tests for downstream consumption and for "ping-pong" design iteration [CAx-IF 58J], or IFC GlobalIds. Otherwise the role is the structural path (assembly path plus entity ordinal), which is weaker.

Exports write persistent IDs derived from `EntityId`s. When a partner adds a chamfer and sends the file back, Crucible matches unchanged entities by ID and shows the partner's change as a diff.

On re-import, Queries resolve by persistent ID first, then by structural path, then by geometric predicates. A failure is the contract's `ResolveError` with candidates; it never silently picks an entity.

### Deterministic export

Writers run in the evaluation context, so an export is a cached `Op` and bit-identical for identical inputs. Three rules make the bytes stable:

1. Header timestamps, such as the STEP `FILE_NAME` time stamp, come from the revision's commit time in `repo`, never from a clock.
2. Instance identifiers, such as STEP `#n` numbers, follow a canonical order of `EntityId`s, so the diff between two exports shows only real changes.
3. Floating-point values use the shortest decimal text that reads back to the same binary value.

A release lists its exported Files with their SHA-256 in the release manifest, and the signed release tag covers them.

### Untrusted content in imported files

Every imported file is untrusted input. Two kinds of risk follow, and translators handle both.

1. **Hostile bytes.** Parsers run as Wasm components with fuel, memory and output limits, so a malformed or malicious file can exhaust only its own budget. Every reader is fuzzed continuously (oracle O-ECO-5).
2. **Hostile text.** Names, notes, PMI text and metadata can carry instructions aimed at agents. Readers return every such string as an `ExternalText` value with its origin, as the AGT tab requires. Imported entities get neutral identifiers such as `part_017`, and the original name is kept as `external(...)` metadata, so foreign names never become Ingot identifiers.

Archive formats (3MF, USDZ, FMU, SSP, OPC-based files) are read with limits on entry count, total expanded size and compression ratio. Paths that escape the archive root fail with `ImportError::UnsafeArchivePath`.

## Standards catalog

### Strategy and fidelity

Every format in the catalog gets exactly one strategy:

- **Build.** Crucible implements the format in Rust as a Wasm component. Where a machine-readable schema exists, the code is generated from it: EXPRESS for STEP and IFC, XSD for the XML formats.
- **Wrap.** An open library under a license compatible with the core is compiled into a Wasm component behind the same WIT world. Wrapping is chosen only when the library is mature and the format is too large to rebuild early.
- **License.** A commercial translator SDK runs as an external tool, outside evaluation (D-ECO-2).

**Decision D-ECO-3:** Open formats are built in Rust as Wasm components, generated from their schemas, and run in the evaluation context on every platform. *Why:* the browser and every desktop then run the same translator bit for bit; one EXPRESS code generator serves STEP AP203, AP214, AP242, AP209, AP238, AP239 and IFC; and Anvil, not a second kernel, interprets the geometry. *Rejected:* wrapping Open CASCADE's STEP translator (LGPL-2.1 [unverified], C++, a second kernel's interpretation between the file and Anvil), which instead serves as an external differential oracle; per-platform native libraries, which break browser parity.

The Rust EXPRESS ecosystem exists but is young. `espr`, an EXPRESS compiler that generates Rust code, reached version 0.4.0 in September 2026 under Apache-2.0 [espr]. Crucible evaluates it as the starting point for its generator in phase 0 and contributes upstream where it fits.

Fidelity is declared per format and direction. The levels are cumulative.

| Level | Preserved | Example |
| --- | --- | --- |
| Visual | Tessellation, appearance, names | glTF export, OBJ |
| Geometry | Exact B-rep, or a mesh with a stated `ErrorBound` | IGES read, STL |
| Structure | Assemblies, Instances, placements, Part identity, properties, materials by name | AP214 read |
| Semantics | Domain meaning: semantic PMI, kinematics, composites, FE models, connectivity, toolpaths | AP242 with semantic PMI, IPC-2581, QIF |
| Identity | Persistent IDs that survive a round trip, enabling incremental exchange and diffs | AP242 persistent IDs, IFC GlobalIds |

The catalog below states versions as checked in October 2026. "Semantics owner" names the tab that defines what the data means; ECO owns the parser, writer, report and oracles. Phases follow contract section 7.

Every row shares one contract, one failure behavior and one oracle pattern. The contract is `read`, `write` and `probe` at the stated fidelity. Failures follow the five rules of the translation report. The oracle is the row's conformance suite in O-ECO-16, plus O-ECO-1 to O-ECO-5 and O-ECO-17 where they apply.

### Mechanical CAD and product data

| Format | Version | R/W | Fidelity target | Strategy | Phase | Semantics owner |
| --- | --- | --- | --- | --- | --- | --- |
| STEP AP242, Part 21 | ISO 10303-242:2025, edition 4, published August 2025; ISO lists it as to be revised, with a committee draft under development [ISO 242] | R/W | Identity: B-rep, assemblies, validation properties, semantic PMI, saved views, tessellation, persistent IDs | Build (contract section 7) | 1: geometry, structure, validation properties, PMI write. 2: PMI read, persistent IDs, tessellated geometry. 3: composites, kinematics | ANV, MEC |
| STEP AP242 edition 5 schema | A separate edition 5 schema, used by CAx-IF round 58J for screw threads [CAx-IF 58J]; ISO lists the next edition as a committee draft [ISO 242] | R/W behind a feature gate | As above, plus semantic threads | Build | 3 | MEC |
| AP242 domain model XML | Used in CAx-IF round 58J for assembly and kinematics data with external Part 21 geometry [CAx-IF 58J] | R/W | Structure: product structure, configurations, kinematics, external geometry references | Build | 3 | `repo`, MEC |
| STEP AP203 | Edition 2; the CAx-IF no longer supports edition 1 [CAx-IF GVP] | R/W | Structure | Build | 1 (R), 2 (W, for legacy receivers) | ANV |
| STEP AP214 | Edition 3 [CAx-IF GVP] | R/W | Structure, colors, layers | Build | 1 (R), 2 (W, for legacy receivers) | ANV |
| STEP AP209 | Described as an extension of AP242 [ISO 10303 wiki]; current edition [unverified] | R/W | Semantics: FE meshes, properties, loads, constraints, results as Fields | Build | 4 | FLX |
| STEP AP238 (STEP-NC) and ISO 14649 | Edition [unverified]; MFG states the scope | R/W | Semantics: workingsteps, machining features, toolpaths, technology | Build | 3 | MFG |
| STEP AP239 (PLCS) | Edition [unverified] | R/W | Structure: breakdowns, configurations, maintenance tasks | Build | 5 | `repo` |
| STEP AP233 (systems engineering) | Edition [unverified] | R | Structure: requirements, functions, system breakdown | Build | 5 | ELX |
| IGES | 5.3 [unverified] | R/W | Geometry: trimmed surfaces, curves, points; subfigures as structure | Build | 1 (R), 2 (W) | ANV |
| JT | ISO 14306-1:2024, edition 1, published August 2024 [ISO 14306] | R/W | Structure, LODs, exact B-rep where present, PMI | License first; CAD Exchanger and HOOPS Exchange both read and write JT [CAD Exchanger formats][HOOPS Exchange]. Own reader from the ISO text later | 2 (License), 4 (Build) | ANV |
| Parasolid X_T, X_B | Vendor format | R/W | Structure, exact geometry | License | 2 | ANV |
| ACIS SAT, SAB | Vendor format | R/W | Structure, exact geometry | License | 2 | ANV |
| CATIA V5 (.CATPart, .CATProduct); CATIA V6 as 3D XML | Version range per translator | R | Structure, plus PMI where the translator supports it | License | 2 | ANV, MEC |
| Siemens NX (.prt) | Per translator | R | As above | License | 2 | ANV, MEC |
| PTC Creo (.prt, .asm) | Per translator | R | As above | License | 2 | ANV, MEC |
| SOLIDWORKS (.sldprt, .sldasm) | Per translator | R | As above | License | 2 | ANV, MEC |
| Autodesk Inventor (.ipt, .iam) | Per translator | R | As above | License | 2 | ANV, MEC |
| Solid Edge; Rhino (.3dm) | Per translator | R (Rhino R/W) | As above | License | 3 | ANV |
| DXF | Version [unverified] | R/W | Geometry: 2D entities, layers, blocks | Build (MEC specifies a pure Rust writer) | 2 | MEC |
| DWG | Vendor format | R; W through a licensed writer [unverified: vendor] | Geometry, 2D | License (MEC) | 3 | MEC |

Crucible never writes native proprietary CAD formats. Exchange back to those systems uses AP242 with semantic PMI and persistent IDs, which the CAx-IF tests for "ping-pong" design iteration [CAx-IF 58J], or Parasolid and JT through the licensed translator.

### Mesh, additive manufacturing and visualization

| Format | Version | R/W | Fidelity target | Strategy | Phase | Semantics owner |
| --- | --- | --- | --- | --- | --- | --- |
| STL | Binary and ASCII; no versions | R/W | Geometry (mesh); `units:` required on read | Build | 1 | ANV |
| OBJ with MTL | No formal versions | R/W | Visual; polygon groups as structure | Build | 1 | UIX (appearance) |
| PLY | Binary and ASCII | R/W | Geometry: meshes and point sets; per-vertex properties become Fields | Build | 1 | ANV |
| 3MF | ISO/IEC 25422:2025. Core 1.4.0; Production 1.1.2; Materials and Properties 1.2.1; Beam Lattice 1.2.0; Boolean Operations 1.1.1; Secure Content 1.0.2; Volumetric 0.8.0; Toolpath 1.0.0, updated 17 September 2026 [3MF specifications] | R/W | Semantics for additive manufacturing: build items, object composition, materials, beam lattices, Boolean shapes; Volumetric and Toolpath version-gated | Build; lib3mf as an external reference oracle [license unverified] | 1 (Core, Production, Materials, Beam Lattice), 2 (Toolpath), 3 (Volumetric, Secure Content) | MFG |
| AMF | ISO/ASTM 52915 [unverified edition] | R/W | Geometry, materials | Build | 2 | MFG |
| glTF 2.0 | ISO/IEC 12113:2022 [Khronos glTF ISO] | W; R later | Visual and structure: scene graph, PBR appearance, instancing; tessellation with stated deviation | Build | 1 (W), 2 (R) | UIX |
| OpenUSD (USDA, USDC, USDZ) | Core Specification 1.0 from the Alliance for OpenUSD, covering grammar, data model, composition and the three file formats; materials, physics and rendering are left to later layered specifications [AOUSD core 1.0] | R/W | Structure and visual; composition arcs preserved on read and flattened only on request | Build against the Core Specification; Pixar's OpenUSD as an external oracle | 3 | UIX |

### Point clouds and scans

A point cloud is a `Body` in the `Mesh` representation with vertices and no faces; intensity, color, normals and scanner ids are `Field`s over it. No point-cloud type is added.

| Format | Version | R/W | Fidelity target | Strategy | Phase | Semantics owner |
| --- | --- | --- | --- | --- | --- | --- |
| E57 | ASTM E2807-11, reapproved [unverified: latest reapproval year] | R/W | Geometry: structured and unstructured scans, scanner poses, attributes as Fields | Build | 3 | MEC (scan-to-CAD) |
| LAS and LAZ | LAS 1.4 (ASPRS) [unverified: current revision] | R/W | As above, plus point classification | Build | 3 | MEC |

### Buildings and infrastructure

| Format | Version | R/W | Fidelity target | Strategy | Phase | Semantics owner |
| --- | --- | --- | --- | --- | --- | --- |
| IFC (STEP physical file) | IFC 4.3 is ISO 16739-1:2024, edition 2, published March 2024 [ISO 16739][buildingSMART IFC 4.3] | R/W | Semantics for steel and timber members, plates, openings, assemblies and property sets; Crucible is not a BIM authoring tool (MEC) | Build with the same EXPRESS generator and Part 21 reader as STEP | 5 | MEC |

### Electronics

ELX owns these formats' semantics and most of their contracts. ECO provides the translator framework, the reports and the oracle harness.

| Format | Version | R/W | Fidelity target | Strategy | Phase |
| --- | --- | --- | --- | --- | --- |
| IDX (ECAD-MCAD) | V6.0; the prostep ivip implementor forum released the schema in December 2025, deferred splines, 3D keep-outs and chamfered board edges to V7, and plans a new version every second year [prostep IDX] | R/W, incremental | Identity: baselines plus change proposals and responses | Build | 4 (ELX) |
| IPC-2581 | Revision C, released December 2020, with bidirectional DFx feedback [IPC-2581C] | W; R of fabricator feedback | Semantics: stackup, layers, netlist, BOM, assembly | Build | 3 |
| ODB++ | ODB++Design 8.1 update 3 [ODB++ 8.1] | W | Semantics, as IPC-2581 | Build, after a format agreement with the owner (ELX open question) | 4 |
| Gerber X2 and X3, Gerber job file, XNC drill | Gerber Layer Format Specification, revision 2026.05 per ELX; the reference page ECO opened still lists 2024.05 [Gerber wiki] | W; R for verification | Semantics: copper, mask, attributes; X3 adds per-part assembly data | Build | 3 |
| KiCad boards, schematics, symbol and footprint libraries | S-expression formats as documented by the KiCad project [KiCad formats] | R; W of libraries | Semantics: connectivity, layout, libraries | Build | 3 |
| EDIF | 2 0 0 [unverified] | W (netlist) | Connectivity | Build | 3 |
| Touchstone, IBIS | Touchstone 2.1 and IBIS 8.0, as ELX cites them | R/W | Semantics: network parameters and buffer models as catalog-part data | Build | 3 |
| VEC (harness) | VEC 2.2.0, as ELX cites it | R/W | Semantics: harness topology, wires, connectors | Build | 4 |
| IPC-D-356, Specctra DSN and SES, pick-and-place CSV | Per ELX | W (DSN also R of SES) | Test netlists; external-router exchange; placement data | Build | 3 |

### Simulation and analysis

| Format | Version | R/W | Fidelity target | Strategy | Phase | Semantics owner |
| --- | --- | --- | --- | --- | --- | --- |
| FMI | 3.0.2, a maintenance release with no new features over 3.0.1; FMUs are compatible across 3.0, 3.0.1 and 3.0.2 [FMI 3.0.2 news]; a 3.0.3 with clock clarifications is announced [Modelica newsletter 2026-02]. FMI 2.0.5 for legacy import [FMI site] | R/W | Semantics: Model Exchange, Co-Simulation, Scheduled Execution | Build (FLX contract) | 3 | FLX |
| FMI layered standards | FMI-LS-XCP 1.0.0; FMI-LS-BUS 1.3.0-beta.1; FMI-LS-STRUCT 1.0.0-rc.1; FMI-LS-REF 1.0.0-beta.1; FMI-LS-DAE 1.0.0-alpha.1 [FMI site] | R; LS-BUS W | Retained and reported when unsupported | Build | 4 | FLX, ELX |
| FMI-LS-WASM | Non-normative prototype that maps the FMI 3.0 C API to the Component Model in WIT [fmi-ls-wasm] | R/W behind a feature gate | Exported FMUs carry a Wasm component binary that runs on every platform | Build; ECO joins the working group | 3 | FLX |
| SSP | 2.0.1 [SSP site] | R/W | Structure: system structure, connections, parameter sets | Build | 3 | FLX |
| CGNS | 4.5.0 [unverified: version taken from distribution packaging] | R/W | Semantics: structured and unstructured CFD meshes, boundary conditions, solutions as Fields | Wrap: the CGNS and HDF5 libraries compiled to a Wasm component [licenses unverified] | 4 | FLX |
| VTK (legacy, XML formats, VTKHDF) | [unverified: current file-format versions] | W; R | Fields on meshes, time series | Build | 2 | FLX |
| Exodus II | [unverified] | R/W | FE meshes, side sets, node sets, results | Wrap, as CGNS | 4 | FLX |
| Nastran bulk data (BDF) | MSC and Simcenter dialects [unverified: dialect versions] | R/W | Semantics: nodes, elements, properties, materials, loads, constraints; results from OP2 as Fields | Build | 3 | FLX |
| Abaqus input (.inp) | Keyword subset [unverified: release] | R/W | As BDF | Build | 3 | FLX |
| OpenFOAM case | Dictionaries and polyMesh for the openfoam.com and openfoam.org lines [unverified: versions] | R/W | Mesh, boundary conditions, fields; solver settings as reported text | Build. OpenFOAM is GPLv3 per COV, so it runs only as an external tool (D-COV-12), never linked | 4 | FLX, COV |
| STEP AP209 | See the mechanical table | | | | | |

**Decision D-ECO-4:** Formats built on HDF5 (CGNS, Exodus II, VTKHDF) wrap the reference C libraries compiled to Wasm components, with HDF5 object time tracking disabled so writes are deterministic [unverified: HDF5 property name and completeness]. *Why:* HDF5 is a large binary container whose reference library is the only complete implementation, and compiling it to Wasm keeps browser parity. *Rejected:* a pure Rust HDF5 subset (large effort, phase 5 at best, revisited if the wrapped library blocks determinism); native libraries (break browser parity).

### Manufacturing and metrology

MFG owns these formats' semantics. ECO supplies reports, oracles and the connector context.

| Format | Version | R/W | Fidelity target | Strategy | Phase |
| --- | --- | --- | --- | --- | --- |
| G-code | ISO 6983-1:2009, which MFG reports ISO confirmed in 2025; vendor dialects declared per `Controller` (MFG) | W; R for verification | Semantics as dialect allows | Build (post-processors are Wasm components, MFG) | 1 |
| STEP-NC | AP238 and ISO 14649 (MFG) | R/W | Semantics | Build | 3 |
| ISO 13399 | Cutting-tool data (MFG) | R | Catalog parts with typed properties | Build | 1 |
| QIF | QIF 3.0, which is ISO 23952:2020 [QIF site]; MFG reports that ISO confirmed it in 2026. DMSC Model-Based Characteristics 1.0 became an ANSI standard on 24 June 2026 [QIF site] | R/W | Semantics: characteristics, plans, results | Build | 2 (characteristics from MBD), 3 (plans and results, MFG) |
| DMIS | [unverified: current ANSI/DMIS version] | W; R of results | Inspection programs | Build | 3 |
| MTConnect | 2.5.0, prepared 5 January 2026 [MTConnect 2.5.0] | R (connector) | Machine state and observations as External inputs | Build | 3 |
| OPC UA, Machine Tools companion | OPC 40501-1 version 1.02.0, released 14 September 2024 [OPC 40501-1] | R; method calls as Acts | As MTConnect | Build | 3 |

### Systems, requirements, robotics and materials

| Format | Version | R/W | Fidelity target | Strategy | Phase | Semantics owner |
| --- | --- | --- | --- | --- | --- | --- |
| ReqIF | 1.2, July 2016 [ReqIF] | R/W | Identity: requirements with external ids, attributes, relations | Build | 4 (ELX) | ELX |
| SysML v2 textual notation | SysML 2.0 and KerML 1.0, approved for final adoption on 21 July 2025 [OMG SysML v2] | R/W | Semantics, mapped to `std::sys` (ELX) | Build | 4 (ELX) | ELX |
| Systems Modeling API and Services | 1.0, approved with SysML v2 [OMG SysML v2] | Server and client | Repository-level exchange with SysML v2 tools | Build as a connector and an `api` facade | 4 | ELX, ECO |
| URDF | ROS convention, no formal versions | W; R | Kinematic tree, inertials, meshes | Build | 4 | ELX |
| SDFormat | 1.12 per ELX [unverified] | W; R | Worlds, closed loops, sensors | Build | 4 | ELX |
| MJCF | Tracks MuJoCo releases [unverified] | W | Bodies, joints, actuators, contacts | Build | 4 | ELX |
| MatML | XML schema [unverified: version] | R/W | Material property records with units and sources | Build | 2 | COV (Material model) |

### Formats not supported

Crucible does not read or write native formats of other tools without a licensed translator, and it never reverse-engineers a proprietary format. It does not import feature history from any system (see "Migration from incumbent tools"). The parts catalog and the package registry are not file formats and appear in their own sections.

## Translator quality

A translator ships only when independent oracles show that it preserves what its catalog row promises. The program has five layers: external interoperability testing, validation properties, round-trip suites, differential testing against other translators, and robustness testing.

### CAx-IF participation

The CAx Implementor Forum is part of the MBx Interoperability Forum, a joint testing effort of AFNeT, PDES, Inc. and prostep ivip [MBx-IF][CAx-IF 58J]. Round 58J ran from March to September 2026 with test cases for assembly-level semantic PMI, composites, kinematics, persistent IDs, hole definitions, surface texture, screw threads, Bills of Operational Features and Model Based Notes [CAx-IF 58J].

The forum's working method sets Crucible's process. Vendors must check STEP files with NIST's STEP File Analyzer and Viewer before submission; files with errors are refused [CAx-IF 58J]. Each file carries native statistics (what the exporter expects) and target statistics (what the importer found), and results are collected in CAESAR [CAx-IF 58J].

**Decision D-ECO-5:** Crucible joins the MBx Interoperability Forum in phase 1 and takes part in every CAx-IF round from then on, beginning with geometry, assembly and PMI-write test cases. Every round's results become regression oracles. *Why:* the forum is where AP242 implementers agree on recommended practices and find each other's bugs; no in-house test replaces testing against CATIA, NX, Creo and other systems' real output. *Rejected:* testing only against public sample files (misses current practices and edition 4 features); waiting for a mature translator before joining (delays the bugs that matter most).

Membership terms and costs are not public [unverified]. Whether round test files may enter Crucible's own oracle corpus depends on those terms (open question 2).

### Validation properties as oracles

The CAx-IF Recommended Practices for Geometric and Assembly Validation Properties, version 4.6 of 21 April 2023, define the properties a sender writes so a receiver can check what it read [CAx-IF GVP]:

- Solids: volume, surface area and centroid.
- Independent surfaces: area and centroid. Independent curves: length and centroid. Independent points: count and centroid.
- Bounding box corners, and clouds of points sampled on individual faces.
- Assemblies: number of children and the notional centroid of the solids.

The practice gives two sets of thresholds [CAx-IF GVP]:

| Property | Interoperability testing (green / yellow / red) | Industry production (OK / not OK) |
| --- | --- | --- |
| Volume, area, curve length | Below 1% / 1–10% / above 10% | 0.5% |
| Centroid | Below 1 mm / 1–5 mm / above 5 mm absolute; or below 0.1% / 0.1–1% / above 1% of the bounding-box diagonal | 0.02 mm plus 0.1% for models over 20 mm |
| Bounding box | Absolute error of both corners | 0.5% |

Crucible uses these properties in three ways:

1. **Every export writes them.** Anvil computes volume, area and centroid with certified integration bounds, so the written value carries a known error far below the production thresholds.
2. **Every import checks them.** Each declared property is compared with Anvil's value and reported (see "Translation report"). Beyond the production thresholds, a warning-severity Check fires.
3. **Corpora become oracles.** On the STEP test corpus, the production thresholds are the pass line. Crucible's internal target is ten times tighter: 0.05% on volume and area (target).

Validation properties do not prove fidelity. A sliver face changes volume by far less than 0.5%, and PMI has no geometric property. Round trips, differential testing and item-by-item PMI comparison cover what properties miss.

### Test corpora

| Corpus | Contents | Use | Access |
| --- | --- | --- | --- |
| NIST MBE PMI test cases | Combined test cases CTC-01 to 05, fully toleranced FTC-06 to 11, simplified STC (2023), hole test case HTC (2024); STEP AP242 and AP203 files plus native CATIA V5, NX, Inventor, Creo and SolidWorks models [NIST MBE PMI] | PMI read and write, item by item; native files qualify licensed translators | Public; MEC reports that NIST permits use without restriction |
| CAx-IF round files | Current-practice files from many CAD systems [CAx-IF 58J] | Interoperability regression | Members [unverified terms] |
| ABC dataset | One million Onshape models; STEP (converted from Parasolid), Parasolid, meshes and FeatureScript for many models [ABC] | Reader robustness at scale; differential testing; migration translators | Copyright stays with the model creators under Onshape's terms [ABC]; used for testing only, never redistributed (open question 10) |
| Held-out corpus | Models never shown to agents (contract section 7) | Final acceptance of every translator release | Protected `oracles/` directory |
| Format suites | 3MF Consortium samples, Modelica Reference FMUs, SSP examples, buildingSMART samples, KiCad demo projects | Per-format conformance | Public [individual licenses unverified] |

### Round-trip and differential suites

| Suite | What it checks | Pass line | Phase |
| --- | --- | --- | --- |
| Self round trip | Write, then read back with Crucible | B-rep surfaces and curves bit-identical; same topology counts; persistent IDs preserved; PMI items equal | 1 |
| External round trip | Crucible writes; a third-party system reads and writes back; Crucible reads | Validation properties within production thresholds; persistent IDs match; partner edits appear as a diff | 2 (via CAx-IF ping-pong cases) |
| Differential read | Crucible's reader against Open CASCADE 8.0.1 [OCCT releases], and from phase 2 against a licensed translator, on the same file | Topology counts equal; Hausdorff distance under the larger of the two file tolerances; every disagreement triaged and recorded | 1 |
| Schema conformance | EXPRESS WHERE and uniqueness rules on every exported file; NIST SFA reports no errors | Zero errors | 1 |
| Export determinism | Two exports of the same revision, on every Tier 1 platform | Byte-identical files | 1 |

Open CASCADE runs only as an external oracle in CI and is never linked into the product. That respects the contract's licensing rule regardless of how OCCT's license is classified [unverified: current OCCT license].

### Robustness

Every reader is fuzzed with structure-aware fuzzers that mutate valid files, plus grammar-based generators for Part 21, XML formats and S-expressions. The pass line is no panic, no unbounded allocation, and termination within fuel on every input. Fuzzing runs continuously; each release needs 10⁹ executions per reader without a new crash (target).

### Licensed translator qualification

A licensed translator version is qualified before an organization can pin it. Qualification runs the NIST native files and the held-out native corpus through it and records topology counts, validation-property deviations and PMI statistics.

The signed qualification record ships with the external tool's package. Builds show it beside every External input that the translator produced, so a reviewer sees how well the translator did on comparable models.

### Translator versions

Translators are packages with semantic versions, like any other Wasm component. A change that alters output bytes for an unchanged input is a behavior change: it needs a new minor version at least, and the changelog flags it. Designs pin translator versions in the lockfile, so an old design re-exports identically, and upgrading shows a diff.

## The extension model

### Three tiers

Contract section 4 fixes the layering. ECO specifies how each tier is built, published and trusted.

| Tier | Purpose | Written in | Runs | Published as | Trust |
| --- | --- | --- | --- | --- | --- |
| Ingot package | Features, Checks, std libraries, standards tables, roles, themes, physics models in weak form | Ingot | Compiled by the Ingot compiler; pure by construction | Package (source) | Typed, pure; cannot reach anything the language does not expose |
| Wasm component | Heavy algorithms: importers, writers, nesting, toolpath strategies, specialist solvers, constitutive models with internal iterations, UI panels, connectors | Rust first; any language that targets the Component Model | In the Wasm sandbox under one of four contexts | Package (Wasm component binary plus a generated Ingot wrapper) | Sandboxed, capability-limited, determinized in evaluation |
| In-tree operation | General primitives used by many packages, and anything needing GPU kernels or SIMD dispatch | Rust in Anvil and Flux | Native, behind a versioned operation contract | Part of the core release | Reviewed in public with oracles (promotion path) |

A third party can contribute an in-tree operation through the same RFC and review process the core team uses. No path into the core exists that a contributor cannot take.

**Decision D-ECO-6:** Authors choose the tier by a fixed rule. Use Ingot unless the code needs one of: more than about 10⁶ primitive steps per call, an existing codebase in another language, or a data structure Ingot cannot express efficiently; then use a Wasm component. Promote to an in-tree operation only when at least three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux's form-level derivatives. *Why:* most logic stays in the most reviewable, most composable tier, and the core grows only where reuse is proven. *Rejected:* letting authors pick freely (heavy code lands in Ingot and slows builds, or trivial logic lands in opaque Wasm components); a native plugin tier (unsafe, per-OS, impossible in the browser).

Wasm components are CPU-only. GPU access from the sandbox would need a deterministic, portable GPU interface, which does not exist; heavy GPU work belongs in Anvil and Flux operations, which have CPU fallbacks.

### Contexts

A context fixes where a Wasm component runs and which capabilities its world may import.

| Context | Runs | Examples | May import | Never imports | Output enters |
| --- | --- | --- | --- | --- | --- |
| Evaluation | Inside Kiln, as an `Op` | Readers, writers, solvers, constitutive models, nesting, toolpath strategies, post-processors | `crucible:geom`, `crucible:field`, `crucible:model`, `crucible:host`, plus type-only interfaces of other `crucible:` packages | All `wasi:` interfaces, `crucible:api` | Kiln, cached under the `Op` key |
| Panel | In the app, on a UI thread budget | UI panels (UIX world `crucible:ui/ui-panel`) | `crucible:api/read`; `crucible:api/edit` when granted | Clocks, random, files, network | The `api`, as ordinary method calls |
| Tool | In a tool runner, outside evaluation | Drivers for external tools, batch migration, source-language translators, local file conversion | `crucible:api`, `wasi:filesystem` on granted directories, `wasi:clocks`, `wasi:random`, `crucible:tool/process` | Network, unless also granted as a connector | External inputs and `api` calls |
| Connector | On a team server or the desktop, outside evaluation | Machine data, supplier offers, manufacturing partners, PLM systems | `crucible:api`, `wasi:http` to declared hosts, `wasi:clocks`, `wasi:random`, `crucible:connect` | Files, process spawning | External inputs, events and Acts |

The evaluation context matches contract section 7: no clocks, randomness, files or network. The registry checks every import against the context's list at publish time, and the host checks it again at instantiation.

### First-party WIT packages

All first-party interfaces live in the `crucible:` namespace. Each WIT package is versioned with SemVer, as WIT package identifiers allow [WIT guide], and published in the registry.

| WIT package | Interfaces | Worlds | Owner |
| --- | --- | --- | --- |
| `crucible:units` | `si`: type aliases such as `length`, `force`, `stress`, `temperature` (kelvin), each an `f64` in SI base units | None | ECO with ING |
| `crucible:geom` | `types` (`body` resource, `entity-id`, `transform`, `error-bound`), `ops` (generated from Anvil's operation catalog), `build` (B-rep, mesh and point construction), `measure` | None | ANV |
| `crucible:field` | `types` (`field` resource, `field-spec`), `build`, `sample` | None | FLX |
| `crucible:model` | `types`, `build` (Parts, Assemblies, Instances, materials by reference, semantic PMI, properties), `read` | None | MEC with `repo` |
| `crucible:host` | `diagnostics` and `progress` (write-only), `cas` (read blobs reachable from inputs), `parallel` (deterministic data-parallel map) | None | KLN |
| `crucible:io` | `types`, `read`, `write` | `importer`, `exporter` | ECO |
| `crucible:physics` | `solve` | `solver` | COV with FLX |
| `crucible:material` | `constitutive` | `constitutive-model` | COV with FLX |
| `crucible:mfg` | `strategy`, `post` | `toolpath-strategy`, `post-processor` | MFG |
| `crucible:ui` | `panel` | `ui-panel` | UIX |
| `crucible:api` | `read`, `edit`, `act`, generated from the method catalog | None | AGT |
| `crucible:tool` | `process`, `external` | `driver` | ECO with PLT |
| `crucible:connect` | `types` (offers, quotes, orders), `external`, `secrets`, `partner` | `connector`, `partner-connector` | ECO with MFG |

**Decision D-ECO-7:** Every first-party WIT package uses the `crucible:` namespace, one package per domain, with American spelling. `flux:constitutive` (FLX) and `crucible:material/behaviour` (COV) merge into `crucible:material/constitutive`, and `flux:solver` (FLX) is the same world as COV's `crucible:physics/solver`. *Why:* one namespace makes ownership and review obvious, and two names for one interface would split the ecosystem. *Rejected:* per-subsystem namespaces such as `flux:` and `anvil:` (parallel naming that tracks internal structure, not domains).

Units do not cross the Wasm boundary as types. A Wasm component's generated Ingot wrapper carries `Quantity<D>` types and converts to SI `f64` values, and the `crucible:units` aliases let the binding generator check that each WIT parameter matches the wrapper's dimension. Absolute temperature crosses as kelvin; the wrapper handles affine conversions.

Strings authored by a Wasm component, such as error details and source entity names, are untrusted. The host wraps every one as an `ExternalText` value with the package as its origin, as the AGT tab requires.

### WIT example: an importer

The importer reads an Asset through a host resource with random access, which zip-based formats such as 3MF need because their directory sits at the end of the file. It emits Crucible's own entities through builders, so the reader never produces a second geometry format.

```wit
package crucible:io@1.0.0;

interface types {
    use crucible:geom/types@1.0.0.{error-bound, heal-policy};
    use crucible:units/si@1.0.0.{length};

    /// The Asset's bytes, supplied by the host.
    resource source {
        size: func() -> u64;
        read: func(offset: u64, len: u32) -> list<u8>;
    }

    record format-info { media-type: string, schema: option<string>, edition: option<string> }

    enum pmi-mode { none, presentation, semantic }

    record read-options {
        units: option<length>,              // required when the format declares none
        heal: heal-policy,
        strict: bool,
        pmi: pmi-mode,
        extra: list<tuple<string, string>>, // format-specific, validated by the reader
    }

    variant disposition {
        exact,
        approximated(error-bound),
        healed(error-bound),
        merged(u32),                        // index of the entry it merged into
        dropped(string),                    // reason
        unsupported(string),                // construct, such as "B_SPLINE_VOLUME"
    }

    record entry { source-ref: string, outcome: disposition }

    enum validation-kind { volume, area, centroid, curve-length, point-count, bounding-box, child-count }
    record declared-validation { source-ref: string, kind: validation-kind, value: list<f64> }

    record read-result {
        entries: list<entry>,
        declared: list<declared-validation>, // validation properties found in the file
        header: list<tuple<string, string>>, // originating system, schema, author fields
    }

    record location { offset: u64, line: option<u32> }
    variant import-error {
        unreadable(location),
        unsupported-schema(string),
        missing-units,
        limit-exceeded(string),
    }
}

interface read {
    use types.{source, format-info, read-options, read-result, import-error};
    use crucible:model/build@1.0.0.{model-builder};

    /// Identify the format from the first bytes only.
    probe: func(head: list<u8>) -> option<format-info>;

    /// Parse `src` and emit Parts, Assemblies and PMI into `out`.
    /// Every source entity must appear in `read-result.entries`.
    parse: func(src: borrow<source>, options: read-options, out: borrow<model-builder>)
        -> result<read-result, import-error>;
}

world importer {
    import types;                          // the host implements the `source` resource
    import crucible:geom/build@1.0.0;      // B-rep, mesh and point construction, validated by Anvil
    import crucible:model/build@1.0.0;     // Parts, Assemblies, Instances, PMI, properties
    import crucible:host/diagnostics@1.0.0;
    export read;
}
```

The geometry builder is where Anvil, not the reader, decides validity. An abridged view:

```wit
interface build {
    use types.{body, error-bound, heal-policy, point3, vector3,
               nurbs-curve, nurbs-surface, oriented-edge, build-error};   // heal-policy: none, conservative, full

    resource brep-builder {
        constructor(tolerance: f64);
        add-plane: func(origin: point3, normal: vector3, x-dir: vector3) -> u32;
        add-nurbs-surface: func(surface: nurbs-surface) -> u32;
        add-curve: func(curve: nurbs-curve) -> u32;
        add-vertex: func(p: point3, tolerance: f64) -> u32;
        add-edge: func(curve: u32, start: u32, end: u32, tolerance: f64) -> u32;
        add-face: func(surface: u32, loops: list<list<oriented-edge>>, same-sense: bool) -> u32;
        add-shell: func(faces: list<u32>, closed: bool) -> u32;
        /// Anvil validates topology and geometry; healing steps return their bound.
        finish: func(heal: heal-policy) -> result<tuple<body, error-bound>, build-error>;
    }
}
```

`build-error` names the offending entity and the failed rule, for example a loop that does not close within its edge tolerances. The reader maps it to a `dropped` or `healed` entry; it never hides it.

The `exporter` world mirrors the importer. Its `write` interface exports `write: func(model: borrow<model-view>, options: write-options, out: borrow<sink>) -> result<write-result, export-error>`. Here `model-view` is a read-only host resource over Parts, Assemblies, PMI and Fields, and `sink` appends bytes to a new CAS blob. `export-error` lists every construct the format cannot carry.

### WIT example: a solver

A specialist solver consumes Bodies and Fields and returns Fields with error estimates and a declared validity envelope. The world name matches the COV tab's `crucible:physics/solver`.

```wit
package crucible:physics@1.0.0;

interface solve {
    use crucible:geom/types@1.0.0.{body};
    use crucible:field/types@1.0.0.{field};

    enum fidelity { interactive, sign-off }

    record request {
        fidelity: fidelity,
        parameters: list<tuple<string, f64>>, // SI values; names and dimensions declared by the Ingot wrapper
        tolerance: f64,                       // target relative error of the outputs
        seed: u64,                            // the only source of randomness
    }

    record error-estimate { value: f64, guaranteed: bool }
    record output { name: string, value: field, estimate: error-estimate }

    variant solve-error {
        outside-envelope(list<string>),       // regime variables outside the envelope
        diverged(u32),                        // iteration at which the residual grew
        invalid-input(string),
    }

    /// Declared validity envelope: (regime variable, lower, upper), SI units.
    envelope: func() -> list<tuple<string, f64, f64>>;

    /// `domain` and `inputs` are handles to immutable, CAS-backed values.
    solve: func(domain: list<body>, inputs: list<field>, req: request)
        -> result<list<output>, solve-error>;
}

world solver {
    import crucible:geom/measure@1.0.0;
    import crucible:field/build@1.0.0;
    import crucible:field/sample@1.0.0;
    import crucible:host/diagnostics@1.0.0;
    import crucible:host/progress@1.0.0;      // write-only: never feeds back into results
    export solve;
}
```

The package ships a generated Ingot wrapper, which a person can then refine:

```
use acme::radiation::{view_factors}

let vf = view_factors(enclosure, faces: enclosure.faces(inner), tolerance: 0.005)
vf.require(vf.reciprocity_error < 0.001)
```

The wrapper turns `outside-envelope` into the contract's `ValidityEnvelope` flag and `solve-error` into typed Ingot errors with fixes. `envelope()` becomes the model's `ValidityEnvelope`.

Rust is the reference language for Wasm components. A Wasm component's crate uses generated bindings and implements the exported interface:

```rust
// Illustrative; generated by the bindings generator from the WIT above.
struct Step;

impl exports::crucible::io::read::Guest for Step {
    fn probe(head: Vec<u8>) -> Option<FormatInfo> {
        head.starts_with(b"ISO-10303-21;").then(step_format_info)
    }

    fn parse(src: &Source, opts: ReadOptions, out: &ModelBuilder)
        -> Result<ReadResult, ImportError> {
        let mut parser = Part21Parser::new(SourceReader::new(src)); // streaming, bounded buffers
        let schema = parser.header()?.schema;                       // AP203, AP214 or AP242
        translate(schema, &mut parser, &opts, out)                  // generated from EXPRESS
    }
}
```

### Capability model

A capability is an imported interface. A Wasm component can call only what its world imports, so the world is its complete permission list.

| Layer | Rule | Enforced by |
| --- | --- | --- |
| Context | Each context allows a fixed set of imports (table above) | Registry at publish; host at instantiation |
| Declaration | The manifest scopes each capability: HTTP hosts, filesystem roots, `api` scopes in the AGT scope model, named secrets | Registry at publish; host per call |
| Grant | A person approves each scoped capability for each package, once per organization or per user, in plain language ("send requests to api.example-supplier.com") | Host; the grant is recorded in the lockfile |
| Policy | An organization allows or denies publishers, capabilities and licenses, can require verified publishers, and can disable the connector context entirely | Team server; desktop and browser apps fetch the policy |

Wasm components in the evaluation context need no grants, because nothing they may import has an effect.

Four rules complete the model:

1. **Escalation needs consent.** An update that adds or widens a capability is never applied automatically. Kiln keeps building with the pinned version, and the update waits as a Proposal that shows the new capability.
2. **Least authority by construction.** Network access is limited to declared hosts by the host's outgoing HTTP handler. Filesystem access is limited to granted directories. Secrets stay in the host: a connector names a secret, and the host attaches it to outgoing requests for the declared host only.
3. **Revocation is immediate.** Revoking a grant stops running instances and fails later calls with `CapabilityDenied { capability, package, fix }`.
4. **Every effectful call is audited.** Tool and connector calls go through the `api` or WASI host interfaces, and the host writes them to the AGT audit log with the package identity.

### Determinism contract

Wasm components in the evaluation context must be bit-reproducible on every platform. Wasm's own semantics leave gaps: NaN bit patterns, relaxed SIMD, memory and table growth, and whatever host imports do [Wasmtime determinism]. Wasm 3.0 adds an optional deterministic profile that fixes the first two once engines implement it [Wasm 3.0].

Wasmtime exposes NaN canonicalization, deterministic relaxed SIMD and fuel as configuration [Wasmtime determinism], but browser engines expose no such controls [unverified], so configuration alone cannot make the browser agree with the desktop.

**Decision D-ECO-8:** The registry determinizes every Wasm component built for the evaluation context at publish time. It validates the binary, rejects nondeterministic features, and injects NaN canonicalization, fuel metering and a stack-depth limiter as ordinary Wasm instructions. Every host executes that determinized binary, and its SHA-256 enters the `Op` cache key. *Why:* engine-independent instrumentation is the only way to get identical results, identical out-of-fuel points and identical stack traps in Wasmtime, in its Pulley interpreter on iPadOS, and in the V8, SpiderMonkey and JavaScriptCore engines in browsers. Bytecode metering is established practice in blockchain runtimes: Parity's `wasm-instrument` injects gas metering and a deterministic stack-height limiter [wasm-instrument], and NEAR's finite-wasm states its goal as runtime-agnostic, deterministic limits on execution time and space [finite-wasm]. *Rejected:* engine fuel such as Wasmtime's (absent from browsers); wall-clock timeouts (nondeterministic); trusting authors to avoid NaN-sensitive code (unverifiable).

The determinizer works in six steps:

1. **Validate.** Reject relaxed-SIMD instructions, shared memories, atomics and threads, and any import outside the context's list. A rejection names the instruction or import and its byte offset.
2. **Canonicalize NaNs.** After every floating-point instruction that can produce a NaN, insert code that replaces any NaN with the canonical quiet NaN of its type, as Wasmtime's `cranelift_nan_canonicalization` does inside its compiler [Wasmtime determinism]. Scalar and SIMD lanes are both covered. When every target engine implements the Wasm 3.0 deterministic profile, this step can be dropped for those engines.
3. **Meter fuel.** Charge a static cost per basic block at block entry, with costs from a published table versioned as `fuel@n`. Bulk-memory instructions are charged in proportion to their length, and host calls charge a cost that the host declares per function. Exhaustion traps with `OutOfFuel { consumed }` at the same instruction on every engine.
4. **Limit stack depth.** Track a logical stack height computed from each function's locals and operand-stack maximum, in the manner of `wasm-instrument`'s stack limiter [wasm-instrument]. The limit traps before any engine's native stack can overflow.
5. **Fix memory and table growth.** `memory.grow` and `table.grow` beyond the declared maximum return −1 on every engine. If the host itself cannot supply memory below that maximum, it aborts the whole evaluation with a host resource error, which Kiln never caches.
6. **Close the boundary.** Hosts canonicalize every NaN they write into a Wasm component's memory or arguments, and the browser glue that the registry generates does the same. NaN payloads therefore never cross the boundary, whatever the Canonical ABI permits [unverified: Canonical ABI NaN rules].

The determinizer and its fuel table are versioned together (`fuel@n`). A new determinizer applies only to new publishes. Stored determinized binaries never change, so a lockfile's pinned hash always names the same bytes.

Instrumentation costs speed. ECO's targets are under 15% overhead for fuel and stack metering combined and under 10% for NaN canonicalization, on the Wasm component benchmark suite (targets). Hot numeric code that needs more should become an in-tree operation through the promotion path.

The contract the host guarantees, for a determinized Wasm component, an export, its arguments, the contents of every resource it can read, and a fuel budget:

- Every conforming host on every Tier 1 and Tier 2 platform produces the same outcome. The outcome is the same return value and the same sequence of host calls, or the same trap at the same point.
- `OutOfFuel`, `StackLimit` and `MemoryLimit` are deterministic outcomes and are cached like results.
- Host resource errors, cancellation and engine faults are not outcomes. Kiln never caches them and reports them as infrastructure failures.
- Randomness comes only from an explicit seed argument, which Kiln derives from the `Op`'s input hashes.
- Host calls into Anvil and Flux operations inherit the operations' own determinism guarantees.

Pure Wasm arithmetic is fully specified once these gaps are closed. A determinized Wasm component therefore produces identical bits across all `PlatformClass`es, which is a stronger guarantee than native code has. ECO asks Kiln to share cached Wasm component results across platform classes when every host call in the trace is itself class-independent (CCR-ECO-4).

Wasm components in the evaluation context have one thread. Kiln parallelizes across `Op`s, and a Wasm component that wants data parallelism imports `crucible:host/parallel`.

Its `map` call runs the same Wasm component's exported `task` function in fresh instances, one per input, and returns the outputs in input order. Each task is a pure function of its input, so the combined result is deterministic.

**Decision D-ECO-9:** Evaluation worlds are synchronous: no `async` functions, streams or futures, and no WASI imports. Tool and connector worlds use WASI 0.3's native async functions, `stream<T>` and `future<T>` [WASI 0.3][WIT guide]. *Why:* evaluation inputs already sit in CAS, so concurrency inside a pure function adds scheduling nondeterminism and nothing else; keeping WASI out of evaluation also insulates the evaluation ABI from the WASI release train. *Rejected:* async evaluation worlds with a deterministic host scheduler (complex to specify and verify, no measured benefit); WASI 0.2 for tool and connector worlds (superseded; its `pollable` model had the composition problem that 0.3 fixes [WASI 0.3]).

### Sandbox limits

Defaults apply per call. A package may request more in its manifest, up to the organization's policy ceiling. Every limit failure is a typed error that names the limit, the amount used and the fix.

| Limit | Evaluation default | Evaluation ceiling | Tool and connector default | Failure |
| --- | --- | --- | --- | --- |
| Linear memory | 1 GiB | 4 GiB (wasm32) | 2 GiB | `MemoryLimit` (deterministic) |
| Fuel | 5 × 10¹⁰ units, roughly 10 to 30 s native (target calibration) | Set by policy | Not metered; wall-clock budget instead | `OutOfFuel` (deterministic) |
| Logical stack | 256 KiB | 1 MiB, calibrated in phase 0 so that every target engine's native stack holds it | Engine default | `StackLimit` (deterministic) |
| Output size | 2 GiB per `Op` output | Policy | Policy | `OutputLimit` |
| Resource handles | 10⁷ live handles | 10⁸ | 10⁶ | `HandleLimit` |
| Wasm component binary | 64 MiB | 256 MiB | 64 MiB | Rejected at publish |
| Wall clock | None in evaluation (cancellation only) | | 15 min per call by default | `Timeout`, not cached |
| UI panel | 2 ms CPU per frame (UIX) | | | Panel paused (UIX) |

Memory64 is not used yet. Wasm 3.0 includes 64-bit memories, limited to 16 GB on the web [Wasm 3.0], but Component Model support for 64-bit memories in every target engine is [unverified]. Work larger than 4 GiB belongs in in-tree operations or in tool-context Wasm components on a server.

### Running on every platform

| Platform | Engine | Notes |
| --- | --- | --- |
| Windows, macOS, Linux (x86-64, ARM64); servers | Wasmtime with Cranelift, in `core/wasm-host` (PLT) | Compiled code cached in CAS by Wasm component hash, engine version and target |
| iPadOS; other targets without JIT | Wasmtime's Pulley interpreter | Same determinized binary; Wasmtime documents roughly a 10× slowdown relative to native code [Pulley] |
| Desktop browsers | The browser's own Wasm engine | At publish, the registry transpiles the determinized Wasm component into ES modules that run on the browser's Wasm engine, as Bytecode Alliance's jco does [jco]. Evaluation worlds import no WASI, so no WASI shim is needed; jco lists its WASI Preview 3 shim for Node.js only [jco]. |

Isolation is layered. Tool and connector Wasm components always run in a separate OS process under PLT's process sandbox.

Evaluation-context Wasm components from verified publishers run in process for speed; those from unverified publishers run in a worker process by default, and organization policy can require that for all third-party Wasm components. An engine bug then exposes at most one sandboxed process.

Tool and connector Wasm components run where their capabilities exist. In the browser they run on the team or cloud server, and on the desktop they run locally. Features are identical; only the location differs.

**Decision D-ECO-10:** The registry builds and signs the browser bundle at publish time, and an oracle checks it against the native result on every test vector. *Why:* browsers do not run Wasm components natively, so transpiling once, centrally and reproducibly is safer than transpiling on every client. *Rejected:* transpiling in the client (slower start, more variance); running Pulley compiled to Wasm in the browser (an interpreter inside an engine, far slower).

### Versioning and ABI stability

WIT packages follow semantic versioning. Feature gates mark the life cycle of each item: `@since(version = …)` items must never change incompatibly, `@unstable(feature = …)` items may change or vanish, and `@deprecated(version = …)` always pairs with another gate [WIT gates].

| Rule | Detail |
| --- | --- |
| Additive minors | A `crucible:` WIT package at 1.x only adds items, each under `@since`. Hosts implement every minor of a major at once. |
| Unstable features | Available only to packages that opt in. Packages that use them publish only as pre-releases. |
| Deprecation window | A deprecated item keeps working for at least 24 months and one edition. |
| Major versions | A new major ships with an adapter Wasm component that implements the old world on top of the new one. Adapters are Wasm components, so they are deterministic and portable too. |
| Retention | Every world major version stays executable for at least 10 years after it is superseded (target, aligned with FLX's retention of behavior versions). |
| Engine changes | A Wasmtime or browser engine upgrade must leave every registry test vector's output hash unchanged before it ships (O-ECO-6). |
| Binary encoding | The registry keeps the original upload and the determinized form. If the Component Model binary encoding changes before its 1.0 [unverified: status], the registry re-encodes stored Wasm components and proves the re-encoded form produces identical results on all test vectors. Lockfiles and cache keys keep the original hash as the Wasm component's identity; the re-encoding is a stored translation with its equivalence record. |

WASI publishes point releases on a two-month train. WASI 0.3.0 shipped on 11 June 2026, outside the train after a subgroup vote; 0.3.1 followed on 11 August 2026, and 0.3.2 is planned for 13 October 2026. The roadmap gives no date for 1.0 [WASI roadmap].

Wasmtime 46 is the first release that implements the final 0.3.0 [WASI 0.3]. Because evaluation worlds import no WASI, only tool and connector Wasm components track this train. Crucible's host supports the current and previous 0.3.x releases at any time.

The lockfile pins each Wasm component by package version and by the SHA-256 of its determinized binary. An old design therefore runs the exact bytes it was built with, on any later host.

## SDKs, CLI, events and repository access

The AGT tab defines the `api` method catalog and makes it the only programmatic surface (D-AGT-1). ECO packages that surface for developers: SDK distribution and stability, a C ABI, the CLI's shape, events and webhooks, and the open formats that let any design leave Crucible.

### SDKs

| SDK | Form | Distribution | Phase |
| --- | --- | --- | --- |
| Rust | Re-exports `core/api` types with an HTTP client and an in-process client (AGT) | crates.io as `crucible-sdk`, plus the Crucible registry mirror | 0 |
| Python | Pure Python, generated from the catalog's JSON Schemas (AGT); fully type-annotated; synchronous and `asyncio` clients | PyPI as `crucible`, with PEP 740 attestations from trusted publishing [PEP 740] | 1 |
| TypeScript | Pure TypeScript, generated from the same schemas; ES modules for Node.js, Deno, Bun and browsers | npm as `@crucible/sdk`, published through trusted publishing [npm security plan] with signed provenance [unverified: npm provenance format] | 1 |
| C ABI | `libcrucible`, a C ABI over the in-process and HTTP clients, for C, C++, C#, Java, Julia, MATLAB and CAD add-ins | Release archives per Tier 1 target with a generated header; NuGet and Maven wrappers later | 2 |

Package names are subject to availability on each public index [unverified].

**Decision D-ECO-11:** The official SDKs are Rust, Python, TypeScript and a C ABI. Every other language binds the C ABI or generates a client from the published JSON Schemas and OpenAPI 3.1 description. *Why:* these four cover systems code, scripting and notebooks, web and agents, and every language with a foreign-function interface; each extra official SDK multiplies parity testing. *Rejected:* official Java, C# and Julia SDKs at launch (the C ABI and generated clients serve them with less upkeep); a Python SDK built on native extensions (AGT keeps the SDKs pure-language so they run wherever their runtimes run).

The SDKs' version equals the catalog version (AGT). The catalog follows SemVer: a minor release only adds methods, optional fields and error codes.

A method is deprecated for at least 12 months before a major release removes it. Servers serve the current and the previous major for at least 24 months.

### API methods that ECO adds

D-AGT-1 makes the `api` catalog the only programmatic surface, so registry, event and archive operations are API methods too. ECO asks AGT to add these to the catalog.

| Method | Contract | Failure behavior |
| --- | --- | --- |
| `registry.search` | Query by name, namespace, world, domain tag, license or badge → package summaries | Empty result with nearest names |
| `registry.get` | Package and version → manifest, capabilities, badges, advisories, output-change labels, docs link | `registry.not_found` with nearest names |
| `registry.resolve` | Manifest plus lockfile → a new lockfile and a diff, without applying it | `registry.unsatisfiable` with the PubGrub explanation and fixes |
| `registry.grant` and `registry.revoke` | Package plus scoped capability → a recorded grant or revocation | `registry.policy_denied` naming the organization rule |
| `registry.yank`, `registry.deprecate` | Publisher-only status changes | `registry.not_owner` |
| `events.list` | Source plus cursor → events in sequence order | `events.cursor_expired` with the oldest available cursor |
| `events.subscribe`, `events.unsubscribe` | Webhook subscription create and delete | `events.url_refused` for non-HTTPS or private addresses |
| `archive.export`, `archive.import` | Design repository ↔ repository archive File | `archive.incomplete` listing missing CAS objects |
| `registry.bundle` | Lockfile → signed offline bundle File for air-gapped sites | `registry.unavailable` naming the packages that could not be fetched |

Publishing a package is an Act (`act.prepare`, then `act.commit`) because it is an irreversible external effect. Its approval step shows the version, the capabilities and the output-change summary.

### The C ABI

The C ABI exists for host applications that cannot call HTTP comfortably, such as CAD add-ins that export to Crucible, PLM plug-ins and test rigs.

```c
/* Illustrative excerpt of crucible.h, generated by cbindgen. */
typedef struct crucible_client  crucible_client;   /* opaque */
typedef struct crucible_stream  crucible_stream;   /* opaque */
typedef struct crucible_buffer  { const uint8_t *ptr; size_t len; } crucible_buffer;

uint32_t crucible_abi_version(void);               /* major << 16 | minor */

crucible_status crucible_client_open(const char *endpoint_utf8, crucible_client **out);

/* Call any API method: canonical JSON request in, canonical JSON response out. */
crucible_status crucible_call(crucible_client *c, const char *method_id,
                              crucible_buffer request_json, crucible_buffer *response_json);

/* Streaming methods (Evaluations) return frames one at a time. */
crucible_status crucible_call_stream(crucible_client *c, const char *method_id,
                                     crucible_buffer request_json, crucible_stream **out);
crucible_status crucible_stream_next(crucible_stream *s, crucible_buffer *frame_json); /* CRUCIBLE_DONE at end */
void crucible_stream_close(crucible_stream *s);    /* cancels the Evaluation if still running */

/* Large CAS objects such as meshes and Field arrays: zero-copy in process, downloaded over HTTP. */
crucible_status crucible_cas_map(crucible_client *c, const uint8_t sha256[32],
                                 crucible_buffer *out);

void crucible_buffer_free(crucible_buffer *b);
void crucible_client_close(crucible_client *c);
```

| Rule | Detail |
| --- | --- |
| Opaque handles | No struct layout is part of the ABI except `crucible_buffer` and plain arrays |
| Strings | UTF-8, null-terminated in arguments, length-delimited in buffers |
| Errors | `crucible_status` codes plus the AGT error object as JSON; Rust panics never cross the boundary |
| Threads | A client handle is thread-safe; a stream handle is used by one thread at a time |
| Stability | Within an ABI major, symbols are only added; removal needs a new major and a new library name (`libcrucible2`) |
| Memory | The library frees what it allocates, through `crucible_buffer_free` |

The C ABI crate sits in `apps/` because it is an FFI boundary. It calls only `api`.

### CLI

The `crucible` binary ships with the desktop app and alone for servers and CI. Its subcommands map one-to-one onto API methods (D-AGT-1). A short set of aliases covers daily work.

| Alias | API method or sequence | Purpose |
| --- | --- | --- |
| `crucible new <template>` | `edit.apply` on a new repository from a template package | Start a design or a package |
| `crucible build` | `evaluate.build` | Build the current revision |
| `crucible check` | `evaluate.checks` | Run every Check; non-zero exit on failure |
| `crucible import <file>` | `edit.apply` that adds the Asset and a `read(...)` expression; for licensed formats, first a tool-context run that records the External input | Import a file, through open or licensed translators |
| `crucible export <target> --format <f>` | `evaluate.build` of a `write(...)` expression | Export a File from CAS |
| `crucible add <package>` | `edit.apply` on the manifest and lockfile | Add a dependency |
| `crucible update [package]` | Resolution, then `edit.apply` | Update the lockfile within the declared ranges |
| `crucible publish` | `act.prepare` and `act.commit` for a package release | Publish to a registry (an Act; see "Publishing") |
| `crucible doc` | `read.docs` | Open local documentation |
| `crucible migrate` | Edition migration, then `edit.apply` | Apply edition fixes (see "Release channels, editions and long-term support") |

| Behavior | Contract |
| --- | --- |
| Output | Human-readable by default; `--json` prints the canonical JSON of the API response |
| Exit codes | 0 success; 1 Check failures; 2 usage error; 3 build error; 4 authorization; 5 infrastructure failure |
| Offline | Works from the local CAS and package cache; `--offline` makes any network need a typed error |
| Air-gapped | Reads packages from an offline bundle or an internal mirror (see "Mirrors, private registries and air gaps") |
| Errors | The AGT error object, rendered with its fixes |

### Events and webhooks

Integrations need to react when things change: a Proposal opens, a release is signed, a package version is yanked, or a catalog part reaches end of life. Crucible emits typed events and delivers them by pull and by push.

**Decision D-ECO-12:** Events use the CloudEvents 1.0 envelope and webhooks follow the Standard Webhooks specification, signed with Ed25519 (`v1a`) by default. Payloads are thin: identifiers, revision hashes and a link, never design content. *Why:* both are open specifications with existing receiver libraries; asymmetric signatures let receivers verify without holding a shared secret; thin payloads mean a leaked endpoint reveals no design data, and receivers fetch content through the `api` under their own scopes and labels. *Rejected:* a custom envelope (no tooling); HMAC-only signing (every receiver holds a secret that can forge events); fat payloads (data leaves through a channel that bypasses access control).

CloudEvents requires `id`, `source`, `specversion` and `type`, with `specversion` set to `1.0`, and producers must keep `source` plus `id` unique per event [CloudEvents]. Crucible sets `source` to the repository, registry or catalog URI, `type` to a reverse-DNS name such as `dev.crucible.proposal.opened` [unverified: domain], `subject` to the object's id, and `time` to the server's record time.

| Event family | Types (examples) | Source |
| --- | --- | --- |
| Repository | `revision.created`, `branch.updated`, `proposal.opened`, `proposal.updated`, `proposal.merged`, `release.signed`, `change_order.approved` | `repo` |
| Evaluation | `evaluation.finished`, `check.failed`, `check.recovered` | Kiln through `api` |
| Act | `act.prepared`, `act.approved`, `act.committed`, `act.failed` | `api` (AGT) |
| Registry | `package.published`, `package.yanked`, `advisory.published`, `publisher.verified` | Registry |
| Catalog | `catalog_part.updated`, `catalog_part.lifecycle_changed`, `offer.changed` | Parts catalog |

Delivery rules:

1. **Pull.** `events.list(source, after: cursor)` returns events in per-source sequence order. Events are retained for at least 30 days (target). This is the reliable path for CI and integration servers.
2. **Push.** A webhook subscription names a source filter, event types and an HTTPS URL. Each delivery carries the Standard Webhooks headers `webhook-id`, `webhook-timestamp` and `webhook-signature`, signed over `msg_id.timestamp.payload` [Standard Webhooks spec]. HMAC-SHA256 (`v1`) is available for receivers that cannot verify Ed25519.
3. **At least once.** Receivers deduplicate by `webhook-id`, which equals the CloudEvents `id`. Failed deliveries retry with exponential backoff and jitter over about three days, following the specification's example schedule [Standard Webhooks spec]. A subscription that keeps failing is disabled with a notice to its owner.
4. **SSRF protection.** Webhook URLs must use HTTPS and must not resolve to loopback, link-local or private address ranges, unless a self-hosted deployment's policy allows named internal hosts. The Standard Webhooks project lists SSRF, spoofing and replay as the attacks to defend against [Standard Webhooks].
5. **Agents.** Agents receive the same events as MCP resource subscriptions (AGT), so both channels carry one event model.

### Repository access and the exit guarantee

Design repositories are reached through the `api` Read, Edit and Propose groups (AGT) and stored by `repo`. ECO adds three surfaces that guarantee no design is trapped (Principle 7).

| Surface | Contract | Phase |
| --- | --- | --- |
| Repository archive | One file holding a design repository's full history: every change, branch, release signature, lockfile and the CAS objects needed to rebuild. Its format is an open, versioned specification published under a permissive license. `api` exports and imports it; restoring it on another deployment reproduces every revision's build hash. | 1 |
| Git mirror | A one-way export of the Ingot sources, manifests and lockfiles to a Git repository, one commit per selected revision, with derived artifacts referenced by hash. It lets teams use Git hosting, code search and audits without Crucible. | 2 |
| Release bundle | Per release: neutral-format Files (AP242 with semantic PMI, 3MF, IPC-2581 and others as configured), the BOM as CSV and JSON, the release manifest with SHA-256 hashes and signatures, and a plain-text index | 1 |

The repository archive format and the CAS encoding of `Body`, `Part`, `Assembly`, `Field` and `Material` are specified openly, so a third party can write an independent reader. O-ECO-12 builds such a reader from the published specification alone and checks it against the reference.

## Package registry

The package registry distributes every package: std, translators, solvers, toolpath strategies, UI panels, roles, templates and catalog-part definitions. The core team publishes through it exactly as anyone else does (Principle 1).

### Names and namespaces

**Decision D-ECO-13:** Every package lives in a namespace that a verified publisher owns. A package's name is `namespace::name`, the same path Ingot uses in `use`. There is no flat global namespace. *Why:* flat registries invite name squatting and typosquatting; namespace ownership tied to a verified domain or organization makes the publisher visible in every `use` line. Maven Central already verifies namespace ownership through DNS TXT records or code-hosting accounts [Maven Central namespaces]. *Rejected:* a flat namespace like crates.io's (squatting, and no visible link between name and publisher); optional scopes like npm's (the unscoped majority keeps the problem).

| Rule | Detail |
| --- | --- |
| Syntax | Each segment is snake_case words that each start with a letter, `[a-z][a-z0-9]*(_[a-z][a-z0-9]*)*`, at most 63 characters. A package path has a namespace and one or more name segments: `acme::radiation`, `parts::ti::tps62133`. |
| One name, three spellings | Ingot: `acme::radiation`. WIT package of its Wasm components: `acme:radiation`. Registry URL path: `acme/radiation`. The mapping is mechanical: WIT uses kebab-case, so `_` becomes `-` and deeper segments join with `-` (`parts:ti-tps62133`). The registry refuses a package whose WIT spelling collides with an existing one. None of the three spellings is a separate name. |
| Namespace claims | By domain (a DNS TXT record on the domain, as Maven Central does [Maven Central namespaces]); by code-hosting organization (OIDC from the host); or as an individual namespace `u_<handle>` for a verified account |
| Reserved namespaces | `std`, `crucible`, `core`, `parts`, `examples`, `wasi`, `test`, and every name starting with `u_` except individual namespaces. `parts` holds catalog-part definitions under supplier sub-namespaces (see "Registry and parts catalog"). |
| Confusables | A new namespace or package within edit distance 1 of a popular one, or equal to it after mapping look-alike sequences (`rn`→`m`, `0`→`o`, `1`→`l`, `_` removed), is held for human review |
| Transfer | Namespaces transfer only with the consent of both parties, or through the dispute policy (trademark or abandonment), and every transfer is published in the transparency log |
| Squatting and lapsed domains | Individual namespaces with no published package after 12 months may be reclaimed after notice. Domain-verified namespaces are re-verified yearly; if the domain lapses or changes hands, the namespace freezes until continuity is proven or a dispute resolves, so an expired domain cannot be used to take over packages. |

### Manifest and lockfile

A package and a design repository share one manifest format and one lockfile format. ECO proposes the names `ingot.toml` and `ingot.lock`; the ING tab owns the module system and may rename them.

```toml
[package]
name        = "acme::radiation"
version     = "1.4.0"
edition     = "2027"
license     = "Apache-2.0"
data-license = "CC-BY-4.0"            # for datasets and tables, when present
description = "Gray-body view factors and radiosity for enclosures"
repository  = "https://git.example.com/acme/radiation"
security-contact = "security@acme.example"

[dependencies]
"std::geom" = "1"
"acme::meshing" = { version = "0.9", registry = "acme-internal" }

[components.view_factors]
path    = "components/view_factors.wasm"   # built by the registry from source when possible
world   = "crucible:physics/solver@1.0.0"
context = "evaluation"
fuel    = 2e11                              # above the default; must fit the organization ceiling

[components.vendor_sync]
path    = "components/vendor_sync.wasm"
world   = "crucible:connect/connector@1.0.0"
context = "connector"
http    = ["api.acme.example"]              # the only reachable host
secrets = ["acme_api_token"]
```

The lockfile records, for every resolved package: name, exact version, registry, the SHA-256 of the source archive, the SHA-256 of each determinized Wasm component and browser bundle, the digest of the signature bundle, and the capabilities granted. It also pins Assets and External inputs by SHA-256. The lockfile is the complete input list that Kiln needs, so a design rebuilds identically wherever its lockfile resolves.

Resolution uses the PubGrub algorithm. When resolution fails, PubGrub returns a derivation tree with the full chain of reasons, from which it builds a human-readable explanation [PubGrub].

Crucible renders that explanation as the typed error, with fixes such as "relax `acme::meshing` to `>=0.8`". ECO proposes that two major versions of one package may coexist in a build, with distinct types and a compiler error naming the conflict when values cross between them; the ING tab decides.

### Versions and compatibility

Versions follow SemVer 2.0. For an engineering platform, compatibility has two parts.

| Kind | Meaning | How it is checked |
| --- | --- | --- |
| Interface compatibility | Public features, types, WIT worlds, parameters, units and defaults | At publish, the registry diffs the public interface against the previous version. A removal or incompatible change in a minor or patch release is refused, naming the item. This follows cargo-semver-checks, which lints Rust API changes for SemVer violations with dozens of lints [cargo-semver-checks]. |
| Output stability | The geometry, Fields and Files a package produces for unchanged inputs | At publish, the registry builds the package's examples and test designs with the old and the new version and records which output hashes changed |

**Decision D-ECO-14:** A release may change outputs, but the registry measures and publishes every output change, and `crucible update` shows it before applying. A patch release that changes outputs is labeled "output-changing" in the index, and organizations can block such updates by policy. *Why:* in physical design, a bug fix that moves geometry is a design change, so it must be visible and reviewable; refusing all output changes in patches would freeze fixes. Lockfiles already pin exact versions, so nothing changes until someone updates. *Rejected:* trusting authors' version numbers alone (silent geometry changes); forbidding output changes outside majors (fixes would wait for breaking releases).

A design's lockfile update is a Proposal like any other change. Its review shows the geometry overlay, metric deltas and Check results (contract section 7, `repo` and UIX), so a package update never changes a design unseen.

### Publishing

**Decision D-ECO-15:** Publishing never uses long-lived tokens. A package is published either from CI through trusted publishing, which exchanges the CI's OIDC identity for a short-lived credential, or interactively with phishing-resistant two-factor authentication. Publishing is an `api` Act, so it is audited like any other external effect. *Why:* crates.io and npm introduced trusted publishing in July 2025 [crates.io update 2025-07][npm security plan]. In September 2025 the Shai-Hulud worm spread through compromised maintainer accounts, and GitHub removed more than 500 compromised npm packages. GitHub then announced that npm publishing would narrow to trusted publishing, local publishing with required 2FA, and granular tokens limited to seven days, with FIDO-based 2FA replacing TOTP [npm security plan]. A new registry can start where those registries are heading. *Rejected:* API tokens with long lifetimes (the main theft target in package-registry compromises); publishing without 2FA (account takeover).

The publish pipeline:

1. The client uploads the source archive, prebuilt Wasm components (optional), the manifest and a signed provenance attestation.
2. The registry verifies the signature, the publisher's ownership of the namespace and the version's novelty. Versions are immutable: a published name and version never changes content.
3. The registry rebuilds Wasm components from source in a hermetic builder when the package declares a supported toolchain. A matching hash earns the "reproduced" badge; a mismatch blocks publication.
4. The determinizer validates and instruments each evaluation-context Wasm component (D-ECO-8), and the transpiler builds the browser bundle (D-ECO-10).
5. Scanners run (see "Security scanning and advisories").
6. Domain acceptance checks run. Tabs contribute them as data, such as COV's checks that every physics model has a validity envelope and its evidence run that assigns evidence levels E0 to E2. The resulting level is shown on the package page.
7. The interface diff and the output-stability run complete (D-ECO-14).
8. The test vectors run on every engine. Results must be bit-identical (O-ECO-6).
9. The registry signs the index entry and appends it to the transparency log.

[[DIAGRAM: Publish pipeline as a left-to-right sequence. Boxes: "Client or CI (OIDC trusted publishing)" -> "Verify signature, namespace, version novelty" -> "Hermetic rebuild (reproduced badge)" -> "Determinize (validate, NaN canonicalization, fuel, stack limit)" -> "Browser bundle" -> "Scanners" -> "Domain acceptance checks" -> "Interface diff and output-stability run" -> "Test vectors on all engines" -> "Sign index entry, append to transparency log". A side branch from every box labeled "typed error, nothing published". Below, three consumer boxes read from the log: "Desktop (Wasmtime)", "iPadOS (Pulley)", "Browser (bundle)", each verifying signature, TUF metadata and log inclusion.]]

A failure at any step returns a typed error naming the step, the cause and the fix. Nothing is published until every step passes.

### Signing, provenance and transparency

| Layer | Mechanism | What it proves |
| --- | --- | --- |
| Author signature | Sigstore keyless signing: Fulcio issues a short-lived certificate bound to the publisher's OIDC identity and an ephemeral key, and the signature is recorded in the Rekor transparency log [Sigstore] | Who published these bytes |
| Build provenance | An in-toto statement with the SLSA provenance predicate `https://slsa.dev/provenance/v1`, signed in a DSSE envelope, as PyPI's attestations do [PEP 740]; SLSA v1.2 is the current approved specification [SLSA] | Which source revision, builder and parameters produced the artifact |
| Registry countersignature | The registry signs every index entry it accepts | That the registry ran every publish check |
| Repository metadata | The Update Framework, which keeps update systems secure even when the repository or signing keys are compromised [TUF] | Freshness and consistency of the index |
| Transparency | All index entries form an append-only log; clients verify inclusion | That no one can serve a version to one user and a different one to another |

**Decision D-ECO-16:** Every package version carries a Sigstore signature and SLSA provenance. Packages under `std::`, `crucible::` and every translator package must be built by the registry's hermetic builder at SLSA Build level 3 [unverified: level definitions in v1.2] and reproduced bit for bit. Third-party packages that do the same receive the "reproduced" badge, and organizations can require it. *Why:* a tampered translator or solver silently corrupts designs, and reproducible builds let anyone check the registry itself. *Rejected:* signatures without provenance (proves who, not what from); GPG keys managed by authors (key loss and poor revocation, which keyless signing avoids).

Private registries in air-gapped sites cannot reach public Sigstore. They run their own Fulcio and Rekor instances or sign with organization-managed keys, and they record their own transparency log [unverified: Sigstore key-based mode details].

### Security scanning and advisories

| Check | When | Action on a finding |
| --- | --- | --- |
| Capability diff | Every publish | A new or widened capability is shown to every dependent organization before their next update (rule 1 of the capability model) |
| Import validation | Every publish | Imports outside the context are refused |
| Network targets | Every connector publish | Declared hosts are compared with known-malicious lists; unexplained new hosts are held for review |
| Secrets in sources | Every publish | Publication refused; the publisher is told which file and line |
| Dependency advisories | Every publish and daily | Dependents are notified; `crucible check` reports affected lockfiles |
| Known-malware signatures and heuristics | Every publish and on signature updates | Version quarantined; human review within 24 hours (target) |
| Fuzzing of importers | Continuously for popular readers | Crashes become private reports to the publisher |

No code runs at install time. Packages have no install scripts and no build scripts that run on the consumer's machine.

Ingot compiles, and Wasm components arrive built and determinized. The Shai-Hulud worm injected malicious post-install scripts into popular packages [npm security plan]; Crucible has no such hook.

Advisories use the OSV schema, version 1.9.1 of 24 September 2026, which RustSec, PyPI, Go and the GitHub Advisory Database already use [OSV]. Crucible asks OSV to add a `Crucible` ecosystem (open question 5).

Crucible adds a second advisory kind for physical products: the **correctness advisory**. It names an operation behavior version, translator version or package version whose outputs were wrong, such as an unconservative stress result or an export that misplaced a hole. Because lockfiles pin every version, `repo` can answer "which released designs used it" exactly, and the advisory lists the affected releases to their owners.

### Yanking, deprecation and removal

| Action | Effect | Who |
| --- | --- | --- |
| Yank | New resolution skips the version; existing lockfiles keep working and the bytes stay downloadable, as in Cargo [cargo yank] | The publisher |
| Deprecate | The package shows a notice and an optional successor; resolution continues | The publisher |
| Advisory | Builds that use the version report a warning Check; `crucible update` proposes the fix | Publisher or registry security team |
| Quarantine | For malicious versions: download stops, and hosts refuse to instantiate the Wasm component; designs that pinned it fail with `PackageQuarantined` and a fix | Registry security team only |
| Legal removal | Content removed for a court order or a license violation; a tombstone keeps the name, version and hash | Registry operators, published in the transparency log |

**Decision D-ECO-17:** Published versions are never deleted by their publishers. Yanking is the only publisher tool. *Why:* released products must rebuild for decades, and a deleted dependency breaks every design that pinned it. npm still allows unpublishing within 72 hours and later under narrow conditions [npm unpublish]; Crucible does not, because a design can be released within hours of a dependency's publication. *Rejected:* a short unpublish window (breaks early adopters' releases); unrestricted deletion (breaks the rebuild guarantee).

Cargo's guidance is that yanking is not the tool for leaked credentials or security fixes [cargo yank]. Crucible's publish flow says the same, and it points the publisher to credential revocation or an advisory instead.

### Mirrors, private registries and air gaps

- **Mirrors are untrusted transport.** Clients verify signatures, TUF metadata and log inclusion, so any HTTP server or CDN can mirror the registry.
- **Private registries** run the same open-source server. A deployment maps namespaces to registries explicitly. A namespace mapped to a private registry never resolves from a public one, which closes dependency-confusion attacks. The Bytecode Alliance's `wkg` tool uses the same kind of namespace-to-registry map [wasm-pkg-tools].
- **Air-gapped sites** import a signed offline bundle produced by `crucible registry bundle --lockfile …`. It contains packages, determinized Wasm components, browser bundles, signatures and a log checkpoint. Bundles can be refreshed incrementally.
- **Standard tooling.** The registry also serves Wasm components in the OCI layout that `wkg` reads, mapping `namespace:name` to `namespace/name` with SemVer tags [wasm-pkg-tools], so standard Component Model tools can fetch Crucible's Wasm components.

### License metadata

Every package declares an SPDX license expression for code and, when it ships data, a separate data license. COV already requires both for physics packages. The registry checks three things at publish:

1. **Validity.** The expression parses, and every file carries a license header or a REUSE-style manifest entry [unverified: REUSE specification version].
2. **Compatibility.** The package's license is checked against its dependencies' licenses. Known conflicts, such as a permissive package that depends on a GPL-3.0 Wasm component, are reported with the reason.
3. **Policy.** Organizations allow or deny licenses. A typical policy denies GPL and AGPL in evaluation-context Wasm components while allowing them in tool-context Wasm components that run as separate programs. This is policy only; the registry does not give legal advice.

A design's release manifest includes a license inventory of every package, translator and dataset it used, so a release ships with its software bill of materials.

### Registry and parts catalog

The package registry distributes software and design data. The parts catalog lists purchasable catalog parts. They differ in ownership, volatility and trust, so they are separate services that share identity, signing and transparency infrastructure.

| Aspect | Package registry | Parts catalog |
| --- | --- | --- |
| Unit | A package version | A catalog part: one orderable item with a manufacturer part number |
| Content | Ingot source, Wasm components, data tables | Definitions (specifications, geometry, SPICE, IBIS and thermal models, lifecycle state, compliance data), plus supplier offers |
| Change rate | Immutable versions | Definitions change rarely; offers (price, stock, lead time) change hourly |
| How a design uses it | Pinned in the lockfile, resolved by PubGrub | The definition is pinned as a package under `parts::`; a parametric selection is a `Query` resolved and pinned (D-ELX-3); offers enter only as dated External inputs (MFG) |
| Publisher | Anyone verified | Manufacturers for definitions; distributors for offers; community contributions labeled as such |
| Trust signal | Signature, provenance, reproduced badge | "Manufacturer-verified" when the definition comes from the manufacturer's own verified namespace |

Each `parts::<manufacturer>` sub-namespace belongs to the manufacturer once it verifies. Until then, the catalog operator curates it, and community definitions enter through review with a "community" label.

**Decision D-ECO-18:** A catalog part's definition is a data package under `parts::<manufacturer>::…`, published and signed through the registry. Its offers are not packages: they are signed feeds that a connector turns into dated External inputs. *Why:* definitions must be pinned and reproducible like code, which the registry already does; offers are volatile and must never make a build depend on the network. *Rejected:* putting everything in the registry (hourly versions of price data); keeping catalog definitions outside the registry (a second signing, versioning and pinning system).

## Marketplace

The marketplace is the registry's commercial layer. It adds paid packages, verified publishers, supplier catalogs and manufacturing-partner integrations without adding a second distribution system.

### Verified publishers

| Level | Requirement | Badge | Grants |
| --- | --- | --- | --- |
| Account | Verified email and phishing-resistant 2FA | None | Individual namespace `u_<handle>` |
| Organization | Domain verified by DNS TXT, or a code-hosting organization verified by OIDC | "Verified organization" | A namespace named after the domain or organization |
| Verified publisher | Organization level plus legal identity checked by the marketplace operator, a security contact, and acceptance of the publisher agreement | "Verified publisher" | Paid packages; manufacturer-verified catalog parts |
| Certified integration | Verified publisher plus an integration test suite passed in Crucible's CI (see "Manufacturing partners") | "Certified" with the suite version | Listing in the UI's ordering and quoting flows |

Badges reflect checks that ran, never quality claims. Each badge links to the dated record of what was checked.

### Paid packages

**Decision D-ECO-19:** Paid packages are ordinary registry packages whose download needs an entitlement. The entitlement is a signed, offline-verifiable token, checked by the host before instantiation and never during evaluation. Once a design pins a paid version, it rebuilds forever with that version. *Why:* evaluation must stay deterministic and offline, and a license server inside a build would break both; designs must not become hostage to a vendor's billing. *Rejected:* runtime license checks inside Wasm components (network in evaluation, and builds fail when a vendor disappears); a separate commercial store (a second package system).

| Rule | Detail |
| --- | --- |
| Entitlement | A signed record of organization, package, version range, seats or usage terms and expiry; verified offline against the marketplace's public key |
| Expiry | Blocks new versions and new installs only. Builds of designs that already pinned a version keep working forever. The registry keeps every paid version downloadable for any organization that ever held an entitlement to it, so a new machine or CI runner can always fetch pinned bytes. |
| Results | Outputs of paid Wasm components are ordinary CAS objects. Sharing a design shares results, not the right to recompute them; a collaborator without an entitlement sees cached results and gets `EntitlementRequired` only when an input changes. Kiln never caches that error. |
| Source availability | Paid packages may ship as compiled Wasm components only. Their worlds, manifests and test vectors are public, so the determinizer and oracles still apply. |
| Escrow | Verified publishers deposit each paid version's source and build recipe with the registry. If the publisher disappears or stops sales for 12 months, existing licensees may rebuild and patch for their own use [unverified: legal enforceability per jurisdiction]. |
| Pricing models | Per seat, per organization or per usage. Usage is metered by the host as counts of evaluation calls, reported outside evaluation; metering never changes results, and a design that pinned a version never stops building because of a usage cap. |
| Refunds and disputes | Governed by the marketplace terms (open question 7) |

The marketplace operator takes a fee on paid sales; the rate is a business decision outside this specification.

### Supplier catalogs

Suppliers publish two things: catalog-part definitions as signed data packages (D-ECO-18), and offers through a connector. Offers follow one record type, `offer` in the `crucible:connect/types` interface, covering price breaks, stock, lead time, minimum order quantity, packaging and validity period. The MFG tab uses offers for costing and sourcing; ELX uses lifecycle and compliance fields for part selection.

| Contract | Detail |
| --- | --- |
| Definition data | Specifications as typed Quantities with tolerances and test conditions; geometry as `Body` with its source format and `ErrorBound`; electrical models; lifecycle state; compliance declarations; datasheet Files by hash |
| Identity | A catalog part's key is (manufacturer namespace, manufacturer part number). Distributor numbers are aliases. |
| Conflicts | When a community definition and a manufacturer definition disagree, the manufacturer's wins for new selections. The difference is listed in the catalog for review. |
| Freshness | Each offer External input has a timestamp. Proposals show when a decision depended on an offer older than a declared age (MFG). |

### Manufacturing partners

Manufacturing partners (CNC shops, sheet-metal shops, print services, PCB fabricators and assemblers) integrate through connector Wasm components that implement one world.

```wit
package crucible:connect@1.0.0;

interface partner {
    use types.{quote-request, quote, order-request, order-status, partner-error};

    /// Price and lead time for a released package of manufacturing data.
    request-quote: async func(req: quote-request) -> result<quote, partner-error>;
    /// Called only through an approved Act (AGT); never from evaluation.
    place-order: async func(req: order-request) -> result<order-status, partner-error>;
    get-status: async func(order-id: string) -> result<order-status, partner-error>;
}

world partner-connector {
    import wasi:http/client@0.3.0;       // name per WASI 0.3 [unverified]; restricted to declared hosts
    import crucible:connect/secrets@1.0.0;
    export partner;
}
```

A `quote-request` names a release by its signed tag and carries content-addressed Files: AP242, 3MF, IPC-2581, drawings and inspection plans as the process needs. Quotes return as External inputs. Orders are Acts, so a human approves the exact action, as the AGT tab specifies.

A partner earns "Certified" by passing a published suite. The suite sends golden-product release packages to the partner's sandbox, checks that the quotes parse, that DFM feedback maps to entities through persistent IDs, and that order status moves through the declared states. Certification records carry the suite version and date, and expire after 12 months.

Partner feedback, such as "hole too close to bend" or IPC-2581 DFx responses, arrives as comments anchored to entities through persistent IDs, as ELX does for fabricator feedback.

## Open-source governance

### License

The contract makes the kernel, language and standard library open source (Principle 7). The choice was between Apache-2.0 and MPL-2.0.

| Criterion | Apache-2.0 | MPL-2.0 |
| --- | --- | --- |
| Copyleft | None | Per file: modified MPL files stay MPL; new files may be proprietary, and static linking into a larger proprietary work is allowed [MPL FAQ] |
| Patents | Express contributor patent license, which terminates for anyone who sues claiming the Work infringes [Apache-2.0] | Patent grants in Section 2, which the FAQ references [MPL FAQ]; retaliation terms [unverified] |
| GPL interaction | The LLVM exception lets combinations with GPLv2 code waive conflicting sections [LLVM exception]; GPLv3 compatibility [unverified: FSF list] | Combinable with (L)GPL through the Secondary License clause unless Exhibit B is used [MPL FAQ] |
| Ecosystem fit | Common in Rust; the Bytecode Alliance's wasm-pkg-tools uses Apache-2.0 WITH LLVM-exception [wasm-pkg-tools], as Wasmtime does [unverified]; `espr` is Apache-2.0 [espr] | Rare in the Rust and Wasm projects Crucible builds on [unverified: survey] |
| Protection against closed forks | None in the license | Only for changes made inside existing files |

**Decision D-ECO-20:** Crucible's code (kernel, language, compiler, Kiln, std, SDKs, WIT packages, registry server and translators) is licensed Apache-2.0 WITH LLVM-exception. Documentation is CC-BY-4.0. Examples and templates are MIT-0, so anyone can copy them into a proprietary design without attribution. Open specifications (the CAS encoding and the repository archive format) are published under a royalty-free patent commitment from the steward [unverified: commitment wording]. *Why:* Crucible's toolchain embeds its own code in artifacts that users distribute, such as generated Wasm component bindings, browser glue and runtime code inside exported FMUs. The LLVM exception waives the conditions of Sections 4(a), 4(b) and 4(d) for exactly that case [LLVM exception]. Apache-2.0's explicit patent license with litigation termination suits a field where patent assertions are expected (the contract already requires a freedom-to-operate review). The license also matches the Rust and Wasm projects Crucible builds on, so every embedder's compliance process already accepts it. *Rejected:* MPL-2.0, because its reciprocity covers only edits to existing files, which a determined closed fork can route around, while its per-file obligations land on every embedder of Anvil and on every generated binding; dual MIT OR Apache-2.0, because MIT carries no patent grant.

Protection against a closed fork comes from three other places: trademarks (a fork cannot call itself Crucible), neutral stewardship (no single company can relicense future versions), and the network effects of the registry and the open formats.

### Contributions

**Decision D-ECO-21:** Contributions are accepted under the Developer Certificate of Origin 1.1, signed off in each commit. There is no CLA and no copyright assignment. *Why:* the DCO certifies that the contributor may submit the work under the project's license [DCO]; Apache-2.0 Section 5 already makes contributions inbound under the same license [Apache-2.0], and Section 3 already grants contributors' patent licenses. A CLA would add friction, require corporate legal review per contributor, and signal a possible future relicensing. *Rejected:* a CLA with copyright assignment (it enables exactly the relicensing that neutral stewardship rules out); no certification at all (weak provenance for a codebase that companies must audit).

Agent-authored contributions follow the same rule. The human principal on whose behalf the agent acted signs off, and the commit records the agent identity and model in a trailer (AGT provenance). Protected paths, including `oracles/`, need human approval (contract section 7).

### Stewardship

**Decision D-ECO-22:** The founding company stewards the project until a fixed trigger, then transfers the repositories, trademarks of the open project and the registry's namespace authority to a neutral foundation. The trigger is the earlier of the phase 3 gate or the first 12-month period in which at least three organizations other than the company employ active maintainers. The commitment is written in the project charter at phase 0. *Why:* engineering organizations keep product data for decades, so they need assurance that the kernel and language cannot be relicensed or abandoned by one company; a foundation also lets competitors invest in a shared kernel. Early company stewardship keeps decisions fast while the architecture settles. *Rejected:* a foundation at launch (governance overhead before there is a community); permanent company stewardship (the main reason large organizations hesitate to depend on a single-vendor open-source project).

The company keeps what it builds on top: hosted services, the marketplace operation, licensed-translator integrations, support and certification delivery. The foundation's choice (a new foundation, or a project under an existing umbrella) is open question 6.

### Teams and decisions

| Body | Members | Decides |
| --- | --- | --- |
| Technical steering committee | 5 to 9 people; at most one third from any single employer after the foundation transfer | Cross-team conflicts, governance changes, team charters, final appeals |
| Area teams | Language (Ingot), Geometry (Anvil), Physics (Flux), Evaluation (Kiln, CAS), Repository (`repo`), API and agents, Interop and ecosystem, Interface, Platform, Standard library | RFCs and reviews in their area |
| Security response team | Appointed by the steering committee | Embargoes, advisories, quarantines |
| Registry operations | Operators of the public registry | Namespace disputes, legal removals, under a published policy |
| Moderation team | Appointed by the steering committee | Code of conduct enforcement |

### RFC process

Significant changes go through public RFCs, modeled on the Rust project's process.

1. **Pre-RFC.** A discussion thread in the area's forum category.
2. **RFC.** A document in the `rfcs` repository with these sections: motivation, design, oracles, determinism and portability, security and capabilities, migration and edition impact, alternatives, prior art, unresolved questions.
3. **Shepherd.** The area team assigns a shepherd within 14 days (target).
4. **Final comment period.** Ten calendar days, opened when no team member objects. Any member may block, giving a reason that the RFC can address.
5. **Decision.** Accepted, postponed or rejected, with a written rationale.
6. **Stabilization.** An accepted feature ships behind an unstable gate. It stabilizes only when its oracles pass on every Tier 1 platform, its docs are complete, and the team approves a stabilization report.

An RFC is required for: new operation families or deprecation of a behavior version; Ingot language changes and editions; new WIT packages, major WIT versions and new capabilities or contexts; registry policies; changes to the license, governance or trademark policy. Bug fixes, new formats inside an approved catalog row, and std additions that follow existing conventions need only review.

Agents may draft RFCs and implement them. Only humans approve RFCs, open final comment periods, and vote.

### Release channels, editions and long-term support

| Channel | Cadence | Support | Output changes |
| --- | --- | --- | --- |
| Nightly | Daily | None | Any |
| Stable | Every 6 weeks | Until the next stable plus 6 weeks | Allowed with changelog; designs keep their pinned behavior versions |
| LTS | One stable per year is designated LTS | 5 years: security fixes, correctness fixes, translator fixes and new platform versions | Only to fix a published correctness advisory |
| Archive | Every stable and LTS | Toolchain containers kept runnable for at least 10 years (target, with FLX and PLT) | None |

**Decision D-ECO-23:** Ingot uses editions, declared per package in the manifest, as Rust does. Packages of different editions interoperate in one build, editions change only surface syntax, the prelude and lint defaults, and `crucible migrate` applies the fixes automatically. An edition never changes the behavior version of an operation that a lockfile pins. *Why:* Rust's edition model allows incompatible surface changes without splitting the ecosystem, because every edition compiles to the same internal representation [Rust editions]; keeping behavior versions out of editions means a migration can be checked by rebuilding. *Rejected:* versioning the whole language in lockstep (forces every package to migrate at once); no editions (the language could never fix early mistakes).

An edition migration must preserve outputs. Every golden product and every registry package's test designs must build to identical output hashes before and after `crucible migrate` (O-ECO-13).

Editions are named by year, at most one every three years (target). The ING tab owns the language rules within an edition.

### Security disclosure

| Item | Policy |
| --- | --- |
| Reporting | `security@` address, a `security.txt` file on project domains [unverified: RFC 9116 details], and private vulnerability reporting on the code host |
| Acknowledgment | Within 2 business days (target) |
| Embargo | 90 days by default; shorter when exploitation is active; longer only by agreement with the reporter |
| Advisories | Published in OSV format with CVSS v4 severity, which OSV supports [OSV]; CVE identifiers requested through a CVE Numbering Authority (open question 12) |
| Scope | Core, std, registry, SDKs, first-party translators and Wasm components, the hosted service |
| Packages | Malicious or vulnerable third-party packages go to the registry security team (see "Security scanning and advisories") |
| Bounty | A paid bug bounty from phase 2, funded by the steward |

Correctness defects that could make a physical product unsafe are handled with the same urgency as security defects. They become correctness advisories with three severities:

| Severity | Meaning | Response |
| --- | --- | --- |
| C1 | A sign-off result is non-conservative, such as an overestimated load capacity, or an export changes manufactured geometry beyond tolerance | Advisory within 72 hours of confirmation (target); affected-release owners notified through `repo` |
| C2 | An interactive-fidelity result or a non-critical export is wrong beyond its stated bound | Advisory with the next stable release |
| C3 | Metadata or presentation errors that do not change geometry or results | Changelog entry |

### Trademarks

The steward claims the open project's names (Crucible, Ingot, Anvil, Flux, Kiln) as trademarks, files for registration after clearance (CCR-ECO-5), and transfers them to the foundation with the project. The policy is published at phase 0.

| Use | Allowed without permission |
| --- | --- |
| Referring to the project, writing about it, teaching it | Yes |
| "for Crucible", "works with Crucible" | Yes, for packages and integrations, if they do not imply official status |
| "Crucible-compatible" | Only for software that passes the published conformance suite for that claim (see "Certification") |
| Modified distributions | Must use a different name; may say "based on Crucible" |
| Package namespaces named after the project (`std`, `crucible`, `core`) | Reserved |
| Logos | Unmodified, for references only |

Two known name collisions need a clearance decision before public launch. Atlassian's Crucible is a code review product whose new sales ended on 13 May 2025 and whose support ends on 15 May 2028 [Atlassian Crucible].

Flux (flux.ai) is a browser-based, AI-assisted PCB design tool [Flux AI], in the same field as Crucible's electronics features. The trademark registration status of either is [unverified]. ECO raises a clearance gate as a contract change request (CCR-ECO-5).

## Documentation and community

### The documentation system

AGT specifies agent-facing documentation: references generated from the Rust method types, Ingot doc comments and the error catalog, pinned to versions, with every example built in CI (D-AGT-23). UIX specifies templates and interactive tutorials verified by scripted solutions. ECO specifies the human-facing documentation system around them and the rules that every package's documentation follows.

**Decision D-ECO-24:** Documentation is organized by the four Diátaxis types: tutorials, how-to guides, reference and explanation [Diátaxis]. Reference is generated, and every code sample in every type is a tested example. *Why:* the four types serve four distinct needs [Diátaxis], so each page does one job; generated reference cannot drift from the code. *Rejected:* a single manual (mixes learning and lookup); a wiki (unversioned, untested).

| Type | Content | Source | Tested by |
| --- | --- | --- | --- |
| Tutorials | Guided first projects, one per golden product, from sketch to release | Tutorial packages (UIX) | Scripted solutions in CI on every release |
| How-to guides | Task recipes: import a supplier's STEP with PMI, write a Wasm importer, publish a package, set up a private registry, migrate from SOLIDWORKS | Markdown with embedded Ingot | Each code block is a built example whose Checks pass |
| Reference | API methods, std features, WIT worlds, error codes, manifest keys, CLI | Generated (AGT pipeline, plus a WIT doc generator) | Coverage gate: every public item has a doc comment, an example and units on dimensional parameters |
| Explanation | Concepts: Body and Field, provenance and Queries, determinism, validity envelopes, capability model, editions | Markdown | Link and example checks |
| Standards notes | One page per catalog format: version, fidelity, known limits and how losses are reported | Generated from the catalog data plus prose | Catalog oracle results shown live |

Every documentation page names the versions it applies to and lives in the same repository as the code it documents. The site is built by the docs pipeline into static HTML, shipped with the desktop app for offline and air-gapped use, and served on the web. Every page links to its source for corrections.

Every package in the registry gets generated reference documentation, built by the registry on publish and pinned to the version. A package's README is shown as `ExternalText` (AGT) unless the publisher is verified.

Localization: the reference and the UI strings ship in English first. Translations of tutorials and explanations are community-maintained per locale, with a freshness indicator that shows when the English source changed.

### Examples

Examples are first-class packages under `examples::`, licensed MIT-0. Each example states what it teaches, builds in CI on every Tier 1 platform, and declares the std version it was last verified against.

Broken examples block a std release. The golden products are published as examples once each milestone closes.

### Community

| Channel | Purpose |
| --- | --- |
| Forum | Questions, RFC pre-discussion, show-and-tell; categories per area team |
| Chat | Real-time help, contributor coordination |
| Issue tracker | Bugs and accepted work, with templates that ask for a minimal design repository archive |
| Office hours | Monthly per area team, recorded with transcripts |
| Conference | Yearly, from phase 3 |

The code of conduct is the Contributor Covenant [unverified: version], enforced by the moderation team with a published process. Contributor ladders run from contributor to reviewer to maintainer, based on sustained review and code work.

### Certification

Certification tests what people and software can do, not what they have attended.

| Certificate | For | Assessment | Validity |
| --- | --- | --- | --- |
| Crucible Associate | Designers | A proctored practical: build a specified Part and Assembly from a brief so that hidden Checks pass, in any editor (GUI, code or agent-assisted, with assistance declared) | 3 years |
| Crucible Professional | Designers and analysts | A practical across design, simulation and release: Checks, a simulation within its validity envelope, and a release package | 3 years |
| Package Developer | Package authors | Publish a Wasm component and an Ingot package that pass the registry's checks, a hidden test-vector suite and a capability review | 3 years |
| Crucible-compatible software | Third-party tools | Conformance suites: AP242 export (validation properties, PMI statistics against NIST cases), repository archive reader, `api` client conformance (AGT golden transcripts) | Per major version |

Assessments are graded by oracles, the same way agent work is. Practical tasks rotate from a held-out pool, so memorized answers do not pass. Certification fees and partner training programs are business decisions outside this specification.

## Migration from incumbent tools

Teams switching to Crucible bring years of models. This section states plainly what moves, what partly moves and what does not.

### What can move

| Source data | Moves as | Fidelity | Path | Phase |
| --- | --- | --- | --- | --- |
| Exact geometry of parts | `Body` (B-rep) with identity | Geometry level: validation properties within production thresholds | AP242, Parasolid or licensed native readers | 1 (STEP), 2 (licensed) |
| Assembly structure | `Assembly` of Instances with placements | Structure level | As above | 1 |
| Semantic PMI | MEC's GD&T model, linked to faces | Semantic level where the source carries semantic PMI; presentation-only otherwise, flagged | AP242 edition 4 or licensed readers with PMI | 2 |
| Mates and joints | Mates where the translator exposes them; otherwise fixed placements, reported | Partial | AP242 kinematics (phase 3) or licensed SDK access [unverified per format] | 3 |
| Properties and metadata | Part identity: item number, name, material by name, custom properties | Structure level | All paths | 1 |
| Drawings | PDF and DXF as Assets; not reconstructed | Visual | Files | 1 |
| PDM history | Released revisions imported as a sequence of `repo` revisions, each with its geometry and metadata | Revision level, without feature history | Licensed PDM connectors or exported revision sets | 4 |

### What cannot move

**Decision D-ECO-25:** Crucible does not import parametric feature history from proprietary systems. It imports geometry, structure, semantic PMI and metadata, and it offers reconstruction of design intent as a reviewed Proposal. *Why:* proprietary feature definitions are vendor- and version-specific, their exact semantics are undocumented, and replaying them without the original kernel gives different geometry; a history that rebuilds differently is worse than no history, because it fails silently. Reconstruction against the imported geometry, by contrast, can be checked. *Rejected:* translating feature trees through licensed SDKs (fragile per version, unverifiable); macro-recording replay (same problem).

Configurations, design tables, equations and sketches also stay behind as live parametric data. Their exported results arrive as geometry. Parameter values that a licensed translator exposes are imported as plain metadata.

### Reconstruction: geometry to features

Reconstruction rebuilds an imported solid as Ingot features. It runs as an agent role (UIX, AGT) and delivers a Proposal reviewed with a geometry overlay against the import.

The pipeline:

1. **Recognize.** Segment the B-rep into machining and modeling features: extrusions, holes with `HoleSpec`, fillets, chamfers, patterns, shells and drafts. Classic rule-based recognition handles prismatic parts. Learned segmentation helps on the rest: BRepNet runs convolutions over oriented coedges directly on the B-rep and outperforms mesh and point-cloud methods on the Fusion 360 Gallery segmentation dataset of over 35,000 annotated models [BRepNet].
2. **Generate.** Write Ingot features that reproduce the recognized structure, using std features and the imported PMI as constraints.
3. **Verify.** Build the generated Part and compare it with the import: Hausdorff distance under a tolerance (default 1 µm, target), equal topology counts, and every semantic PMI item re-attached through a `Query`.
4. **Fall back.** Regions that do not verify stay as imported geometry, combined with recognized features through Anvil's direct-edit operations, and the report lists them.

The reconstruction quality target is that at least 9 of the 11 NIST CTC and FTC parts, and 80% of a held-out set of prismatic parts, rebuild fully with all PMI re-attached by the phase 3 gate (target).

### Translating source languages

Some incumbent tools store designs as code. Code can be translated far more faithfully than feature trees, because its semantics are visible.

| Source | Status | Approach | Phase |
| --- | --- | --- | --- |
| Onshape FeatureScript | Onshape's feature language [unverified: public reference and terms for translation]; the ABC dataset ships FeatureScript for many models [ABC] | Translator from FeatureScript to Ingot covering the std feature calls, units and sketches; unknown library calls become stubs that fail with `Untranslated` and keep the original as a comment | 4 |
| Zoo KCL | Zoo documents KCL as the language of the Zoo Design Studio, with functions, pipelines, sketch blocks and units [KCL docs]; its license is [unverified] | Translator from KCL to Ingot; pipelines map to Ingot's `\|>` | 3 |
| OpenSCAD | Open language [unverified: license] | Translator to Ingot for CSG, extrusions and modules; mesh-only constructs map to `Mesh` Bodies | 2 |
| CadQuery and build123d (Python on Open CASCADE) | Open source [unverified: licenses] | Runs the source as an external tool in a pinned container, captures the operation trace, and emits Ingot for recognized calls; the rest becomes imported geometry | 3 |
| Spreadsheet-driven design tables | Data | Imported as Ingot parameter files and variant sets | 2 |

Each translator runs in the tool context: as a Wasm component, or as an external tool when it needs a foreign runtime such as Python and Open CASCADE. Translation is verified like reconstruction: the translated Ingot must build and match the geometry that the original tool produced, exported to STEP, within tolerance.

### Tooling for switching teams

| Tool | What it does | Phase |
| --- | --- | --- |
| `crucible import scan <dir>` | Inventories a file tree or PDM export: formats, versions, assemblies, broken references, duplicate parts by geometry hash; estimates translator needs | 2 |
| Bulk import | Converts an inventory into design repositories, one per product, with Assets, External inputs and import Checks; runs on team servers, resumable, with a per-file report | 2 |
| Parallel run | Keeps the incumbent system authoritative while Crucible re-imports each new release and reports differences, so teams switch on evidence | 3 |
| Concept guide | Maps incumbent concepts to Crucible's (UIX) | 1 |
| Library migration | Converts standard-part libraries and title blocks to packages; maps vendor catalog references to `parts::` definitions | 3 |
| Round-trip bridge | Exports AP242 with persistent IDs to the incumbent tool and imports changes back, so mixed teams can work during the transition | 3 |

Migration never deletes or modifies the source data, and every converted model keeps its source File by hash as provenance.

## State of the art

Targets are labelled as targets. "Leading implementation" names what Crucible must match or beat on the stated measure.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| STEP AP242 reader and writer | Schema-generated bindings from EXPRESS; CAx-IF recommended practices for PMI, validation properties and persistent IDs [CAx-IF GVP][CAx-IF 58J] | Commercial translators that test in CAx-IF rounds; Open CASCADE 8.0.1 as the open baseline [OCCT releases] | Own Rust reader and writer generated from EXPRESS (D-ECO-3), tested in every CAx-IF round (D-ECO-5) | CAx-IF round results; validation properties on the corpus at 0.05% (target, 10× tighter than production); zero NIST SFA errors; PMI statistics equal to native statistics on all NIST cases |
| STEP read throughput | Streaming Part 21 parsing with lazy entity resolution | Open CASCADE (differential) | Streaming parser with bounded buffers, parallel entity translation, deterministic merge | Throughput on a 1 GB AP242 file: at least 2× Open CASCADE on the reference laptop (target); browser within 3× of native (target) |
| Proprietary CAD import | Vendor SDK access to native files | CAD Exchanger, HOOPS Exchange, Datakit [CAD Exchanger formats][HOOPS Exchange][Datakit] | License, out of process, results pinned as External inputs (D-ECO-2) | Qualification on NIST native models and the held-out native corpus: topology counts, validation properties, PMI statistics |
| Validation and repair | Validation properties as receiver-side oracles [CAx-IF GVP]; explicit healing with bounds | Commercial healing tools [unverified: names] | Anvil healing operations with `ErrorBound`, reported per entity | Every healed entity has a bound; re-export passes validation properties at production thresholds |
| Sandboxed extensions | WebAssembly Component Model with WIT; WASI 0.3 native async for effectful worlds [WASI 0.3] | Wasmtime 46 [WASI 0.3]; jco for browsers [jco] | Component Model everywhere; synchronous, WASI-free evaluation worlds (D-ECO-9) | Conformance of every first-party world on Wasmtime, Pulley and three browser engines |
| Deterministic execution | Wasm 3.0 deterministic profile [Wasm 3.0]; NaN canonicalization and deterministic relaxed SIMD in Wasmtime [Wasmtime determinism]; bytecode-injected metering [wasm-instrument][finite-wasm] | Wasmtime with fuel (native only) | Publish-time determinizer that works on every engine (D-ECO-8) | Bit-identical outputs and trap points on 10⁴ test vectors across all engines; overhead under 15% for metering and under 10% for NaN canonicalization (targets) |
| Interpreter fallback | Portable bytecode interpreter | Wasmtime Pulley, about 10× slower than native [Pulley] | Pulley on iPadOS and non-JIT targets | Same outputs; slowdown measured per class of Wasm component |
| Supply-chain signing | Sigstore keyless signing with Rekor transparency [Sigstore]; SLSA v1.2 provenance [SLSA]; PEP 740 attestations [PEP 740]; TUF metadata [TUF] | PyPI attestations; npm and crates.io trusted publishing [npm security plan][crates.io update 2025-07] | All of these, mandatory for every package (D-ECO-15, D-ECO-16) | 100% of index entries verifiable offline; reproducible rebuild of every first-party package |
| Dependency resolution | PubGrub with derivation-tree explanations [PubGrub] | uv and Cargo resolvers [unverified: algorithm details] | PubGrub; explanations as typed errors with fixes | Resolution of the full registry graph under 1 s (target); every failure explained |
| Semver enforcement | Rustdoc-JSON-based linting [cargo-semver-checks] | cargo-semver-checks | Interface diff at publish, plus output-stability measurement (D-ECO-14) | Seeded breaking changes all caught; zero false refusals on a curated set |
| Vulnerability data | OSV schema 1.9.1 [OSV] | OSV.dev, RustSec, GitHub Advisory Database | OSV format plus correctness advisories | Advisory-to-lockfile match latency under 1 h (target) |
| Webhooks and events | Standard Webhooks [Standard Webhooks spec]; CloudEvents 1.0 [CloudEvents] | Large SaaS webhook platforms [unverified] | Both, Ed25519 by default (D-ECO-12) | Conformance with the reference verifier libraries; delivery success under fault injection |
| Feature recognition for migration | B-rep message passing: BRepNet [BRepNet]; rule-based recognition for prismatic parts | Commercial feature recognition in CAD tools [unverified: names] | Rules plus learned segmentation, verified by rebuild (D-ECO-25) | NIST CTC and FTC parts: at least 9 of 11 fully rebuilt with PMI by the phase 3 gate (target) |
| ECAD-MCAD exchange | IDX V6 incremental exchange [prostep IDX] | Commercial ECAD and MCAD pairs in the implementor forum | Build IDX V6 as a Wasm component (ELX, phase 4) | Implementor-forum scenarios [unverified: access]; round trip of baselines |
| Co-simulation exchange | FMI 3.0.2 and SSP 2.0.1; FMI-LS-WASM prototype [FMI site][fmi-ls-wasm] | FMPy and others (FLX) | Native importer and exporter (FLX); Wasm FMUs through LS-WASM | Modelica Reference FMUs on every Tier 1 OS (FLX); LS-WASM prototype examples |
| Documentation | Diátaxis [Diátaxis]; generated, tested reference | Rust's docs.rs and doc tests [unverified as a benchmark] | Diátaxis, tested examples, offline docs (D-ECO-24) | Coverage gate at 100%; every example builds on every release |

Deviations from the state of the art, with reasons:

- **Licensed translators run outside evaluation** rather than inside builds. Reason: determinism and portability.
- **Wasm components are CPU-only.** Reason: no deterministic, portable GPU interface exists for sandboxed code.
- **No memory64 in Wasm components yet.** Reason: maturity; Component Model support across all target engines is unverified.
- **HDF5-based formats wrap the C reference library** rather than a pure Rust implementation. Reason: maturity.

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| All Tier 1 | Translator behavior differing by platform | Open-format translators are determinized Wasm components; exports are byte-identical everywhere (O-ECO-4) |
| Windows, macOS, Linux | Licensed translator SDKs exist only for some OS and architecture pairs; CAD Exchanger's format page, for example, marks 3DS as Windows-only [CAD Exchanger formats], and HOOPS Exchange lists Windows, Linux and macOS with limited iOS and Android support [HOOPS Exchange] | Licensed translators run on any desktop where the vendor ships them, otherwise on a team or cloud server. The External input they produce is identical wherever it is used, so features stay identical. |
| Windows ARM64 | Vendor SDK availability for ARM64 is [unverified] | Same fallback to a server; x64 emulation only if the vendor supports it |
| macOS | Wasmtime's JIT needs the hardened-runtime JIT entitlement (PLT) | PLT ships the entitlement; Pulley remains the fallback |
| Browsers | No native Component Model; 4 GiB wasm32 memory ceiling (PLT); no local tool or connector context | Registry-built browser bundles (D-ECO-10); tool and connector Wasm components run on the team or cloud server; large imports run as server Evaluations that fill the shared cache |
| Browsers | Local files reach the app only through file pickers and drag and drop | Imports upload the bytes to CAS first, then evaluate; the Asset hash is identical to a desktop import |
| iPadOS | No JIT for App Store apps; App Review guideline 2.5.2 on downloaded code (PLT) | Pulley interpreter; Wasm components from the registry count as data executed by an interpreter. Whether App Review accepts downloaded Wasm components is [unverified] (open question 9). |
| Android | JIT allowed [unverified: current Play policy for downloaded code] | Wasmtime with Cranelift where policy permits; Pulley otherwise |
| Air-gapped installs | No Sigstore, registry or translator license servers | Offline registry bundles with a private signing root; translator licenses with offline activation where the vendor offers it [unverified per vendor]; entitlements verified offline |
| Paths and text in files | Unicode normalization, line endings and code pages differ inside imported files | Readers decode text per the format's declared encoding, normalize names to NFC through the platform layer's single implementation, and record the original bytes |

## Interfaces with other subsystems

### Consumed

| From | What ECO needs | Types |
| --- | --- | --- |
| ANV | Builders for B-rep, mesh and point Bodies with validation and healing that return `ErrorBound`s; certified volume, area and centroid integration; `HistoryRecord`s for import Ops; deterministic tessellation for visual exports | `Body`, `EntityId`, `ErrorBound`, `HistoryRecord` |
| MEC | The semantic GD&T model and its AP242 mapping table; `ShapeAspect`; kinematic joints for AP242 kinematics; composites; drawing exports | `Tol<T>`, `Part`, `Assembly` |
| FLX and COV | Field encodings for AP209, CGNS, Exodus, VTK, BDF, Abaqus and OpenFOAM; FMI and SSP semantics; the `crucible:physics` and `crucible:material` worlds' semantics | `Field<Domain, V>`, `Material`, `ValidityEnvelope` |
| ELX | Board, netlist and library models; IDX, IPC-2581, ODB++, Gerber, KiCad and EDIF semantics; SysML v2 and ReqIF mapping; robot description semantics | `Part`, `Assembly`, `Instance` |
| MFG | Toolpath and machine models; G-code dialects; QIF characteristics; offer usage; partner flows | `Part`, `Assembly` |
| ING | The module system, `use` paths, manifest and lockfile ownership, editions within the language, generated wrapper conventions for Wasm components, `Quantity<D>` mapping to SI | `Feature`, `Quantity<D>` |
| KLN | Leaf inputs for Assets and External inputs; Wasm component execution as `Op`s keyed by the determinized hash; non-caching of host resource errors | `Op` |
| `repo` | Lockfile storage; repository archive export and import; release manifests and signatures; queries for "which releases used version X" | Proposal, release |
| AGT | The `api` method catalog, Acts and approvals, `ExternalText`, audit log, MCP subscriptions | API method |
| PLT | `wasm-host` with Wasmtime and Pulley; the process sandbox for tool and connector contexts; offline bundle handling; the single text-normalization implementation | `PlatformClass` |
| UIX | Rendering of translation reports, capability grants, package pages, marketplace flows | — |

### Provided

| To | What ECO provides |
| --- | --- |
| All tabs | The standards catalog and the `io/` translator framework; `read`, `write` and `probe`; `TranslationReport` |
| All tabs | The first-party WIT packages under `crucible:`, the four contexts, the capability model, the determinism contract and sandbox limits |
| All tabs | The package registry: names, versions, signing, provenance, scanning, yanking, mirrors, licenses |
| KLN | Determinized Wasm component hashes for cache keys; the guarantee that determinized Wasm components are class-independent |
| AGT | Package signing and provenance for `std::agents` and `std::explore`; license metadata for packages and datasets; events for subscriptions |
| ELX and MFG | The parts catalog's publishing path for definitions (`parts::`) and the offer connector schema |
| FLX and COV | Registry hosting for solver and constitutive Wasm components; FMU and SSP packaging rules, including FMI-LS-WASM binaries |
| UIX | Package metadata, capability descriptions and badges for display; tutorial and template packaging |
| PLT | Requirements for `wasm-host`: determinized execution, fuel and stack instrumentation, and the browser bundle format |
| Everyone outside | SDKs, the C ABI, the CLI, events and webhooks, the repository archive format, the CAS encoding specification |

## Oracles

All ECO oracles live in `oracles/eco/`, which agents can read but not write (contract section 7). Corpora that agents must never see live in the held-out store.

| Id | Claim | Method | Pass line | Phase |
| --- | --- | --- | --- | --- |
| O-ECO-1 | STEP readers preserve geometry | Read every corpus file (AP203, AP214, AP242); compare declared validation properties with Anvil's values | All within CAx-IF production thresholds; 95% within 0.05% on volume and area (target) | 1 |
| O-ECO-2 | Semantic PMI survives export and import | NIST CTC, FTC, STC and HTC rebuilt natively (MEC-O-DR-3), exported, re-imported and compared item by item; PMI statistics compared with native statistics | Every item equal in type, value, tolerance, datum references and target faces | 1 (write), 2 (read) |
| O-ECO-3 | Exported files conform to their schemas | EXPRESS rule checks, NIST STEP File Analyzer and Viewer, XSD validation for XML formats, consortium validators where they exist | Zero errors | 1 |
| O-ECO-4 | Exports are deterministic | Export every golden product in every catalog format on every Tier 1 platform, including the browser | Byte-identical Files | 1 |
| O-ECO-5 | Readers survive hostile input | Structure-aware and grammar-based fuzzing of every reader | No panic, no allocation beyond limits, termination within fuel; 10⁹ executions per reader per release without a new crash (target) | 1 |
| O-ECO-6 | Wasm components behave identically on every engine | 10⁴ recorded test vectors per first-party Wasm component, run on Wasmtime (x86-64, ARM64), Pulley, V8, SpiderMonkey and JavaScriptCore; also run before any engine upgrade | Identical outputs, host-call sequences and trap points, including `OutOfFuel` at the same consumed count | 0 |
| O-ECO-7 | The determinizer is sound | The WebAssembly specification test suite run before and after determinization; a seeded corpus that observes NaN bits, uses relaxed SIMD, grows memory and recurses deeply | Spec tests pass except NaN-payload assertions, which yield the canonical NaN; forbidden features refused with offsets; seeded programs agree across engines | 0 |
| O-ECO-8 | Capabilities hold | A red-team corpus of Wasm components that import forbidden interfaces, reach undeclared hosts, escape directories, read secrets or call `api` beyond their scopes | Every attempt refused, typed and audited; no data leaves | 1 |
| O-ECO-9 | Registry integrity | Tamper tests on a staging registry: altered bytes, rollback, freeze, mix-and-match metadata, split views, forged provenance; reproducible rebuild of every first-party package | Clients detect every tampering; rebuilt hashes equal published hashes | 1 |
| O-ECO-10 | Compatibility gates work | Seeded breaking interface changes and seeded output changes published as minor and patch releases | All breaking changes refused; all output changes labeled | 1 |
| O-ECO-11 | SDKs and C ABI agree | AGT golden transcripts replayed through the C ABI as well as Rust, Python and TypeScript (extends O-AGT-2); ABI symbol diff per release | Byte-identical canonical JSON; no symbol removed within an ABI major | 2 |
| O-ECO-12 | Designs can leave | An independent reader, written in another language from the published specifications alone, reads repository archives and CAS encodings of the golden products | Same revision count, same Body measurements within `ErrorBound`, same BOM | 1 |
| O-ECO-13 | Edition migration preserves outputs | `crucible migrate` on every golden product and every registry package's test designs | Identical output hashes before and after | Each edition |
| O-ECO-14 | Events and webhooks are reliable | Fault injection: receiver down, slow, returning errors, duplicate deliveries; verification with Standard Webhooks reference libraries; SSRF probes | At-least-once delivery, deduplication by id, signatures verify, every SSRF probe refused | 1 |
| O-ECO-15 | Licensed translators are qualified | Rerun the qualification suite for every translator version an organization pins | Qualification record reproduces; thresholds met or the version is flagged | 2 |
| O-ECO-16 | Every catalog row works | One conformance suite per catalog row (3MF samples, Modelica Reference FMUs through FLX, SSP examples, IFC samples, KiCad projects, Gerber and drill re-reading through ELX); the catalog page is generated from the results | Every row at or below the current phase passes | 1 onward |
| O-ECO-17 | Nothing is lost silently | For every corpus file, count source entities by kind and compare with the report's entries | Every source entity accounted for | 1 |
| O-ECO-18 | Imported text stays untrusted | An injection corpus in names, PMI text, notes and metadata of every text-bearing format (shared with AGT) | No imported string reaches an Ingot identifier, error text or agent context except as `ExternalText` | 1 |
| O-ECO-19 | Installing runs no code | Trace `crucible add` and `crucible update` on test packages | No package code executes; only downloads and verification | 1 |
| O-ECO-20 | Paid packages never block rebuilds | Build designs with paid packages offline, with valid, expired and revoked entitlements | Pinned designs rebuild in all cases; new versions blocked when not entitled | 3 |
| O-ECO-21 | Migration reconstruction is checked | Reconstruction of the NIST CTC and FTC parts and a held-out set of prismatic parts | At least 9 of 11 NIST parts and 80% of the held-out set rebuild fully within 1 µm with all PMI re-attached by the phase 3 gate (target); the rest report their unverified regions | 3 |
| O-ECO-22 | Old designs re-export identically | Re-export archived golden-product releases from every earlier stable and LTS release with their pinned versions | Byte-identical to the archived Files | 2 onward |

## Phasing

| Phase | ECO deliverables | Gate contribution |
| --- | --- | --- |
| 0, foundations | First-party WIT packages at 0.x (`units`, `geom`, `field`, `model`, `host`, `io`); determinizer and test-vector harness; `wasm-host` integration with PLT on Wasmtime, Pulley and the browser bundle; EXPRESS code generator chosen and the Part 21 parser built; STL, OBJ and PLY; registry prototype with namespaces, lockfile and Sigstore signing; Rust SDK packaging; license, DCO, project charter with the stewardship commitment, trademark and security policies | O-ECO-6 and O-ECO-7 green, which is part of the determinism suite |
| 1, wedge | STEP AP242 (geometry, structure, validation properties, semantic PMI write) and AP203 and AP214 read; IGES read; 3MF Core, Production, Materials and Beam Lattice; glTF write; translation reports; CAx-IF membership and first round; public registry with trusted publishing, provenance, TUF and transparency log; Python and TypeScript SDKs; CLI; events and webhooks; repository archive and release bundles; docs site, examples and certification design | Golden products 1 and 2 release bundles: AP242 with semantic PMI passing O-ECO-1 to 4; 3MF with beam lattice passing consortium validation |
| 2, mechanical depth | Licensed translators for CATIA, NX, Creo, SOLIDWORKS, Inventor, Parasolid, ACIS and JT; AP242 PMI read and persistent IDs; IGES write; glTF read; AMF; VTK; MatML; QIF characteristics from MBD (MFG); 3MF Toolpath; C ABI; Git mirror; private registries, mirrors and air-gap bundles; verified publishers and free marketplace listings; `crucible import scan` and bulk import; OpenSCAD translator; Associate certification; first LTS release at the gate | Golden products 3 and 4 exchanged with an external CAD system by AP242 round trip with persistent IDs |
| 3, product breadth | Electronics formats (IPC-2581, Gerber X2 and X3, KiCad, EDIF, Touchstone, IBIS, IPC-D-356, Specctra); FMI 3.0.2, SSP 2.0.1 and FMI-LS-WASM (FLX); Nastran BDF and Abaqus input; QIF results and DMIS; STEP-NC; MTConnect and OPC UA connectors; 3MF Volumetric and Secure Content; OpenUSD; E57 and LAS; AP242 composites, kinematics and edition 5 threads; KCL and CadQuery translators; reconstruction pipeline; paid packages, supplier catalogs and certified manufacturing partners; Professional and Package Developer certification; foundation transfer at the latest at this gate (D-ECO-22) | Golden product 5 released with IPC-2581, Gerber X2 and AP242 of the board and enclosure from one design repository (D-ELX-7 makes IDX unnecessary inside Crucible) |
| 4, full multiphysics | AP209; CGNS and Exodus II; OpenFOAM cases; ODB++; IDX V6 export, baseline import and change proposals; VEC; ReqIF; SysML v2 text and the Systems Modeling API; URDF, SDFormat and MJCF; FMI layered standards; FeatureScript translator; PDM history import; own JT reader | Golden product 6 FE and CFD models exchanged with an external solver, and its robot description loaded by an external simulator |
| 5 and later | IFC 4.3 (with MEC's golden product 7); AP239 and AP233 | Golden product 7 exchanged through IFC 4.3 |

## Open questions

1. **Translator vendor.** Which licensed translator comes first: CAD Exchanger, HOOPS Exchange or Datakit? The deciding terms are permission to run out of process on team and cloud servers, permission to store translated geometry as External inputs that collaborators without a license can rebuild from, ARM64 and Linux builds, and offline activation for air-gapped sites. None of these terms is public [unverified].
2. **CAx-IF terms.** What do MBx-IF membership and CAx-IF participation cost, and may round test files enter Crucible's protected oracle corpus? If not, which files can be regenerated natively from the round specifications?
3. **EXPRESS sources and generator.** Under what terms may the AP242 edition 4 and edition 5 EXPRESS schemas be used for code generation and redistribution of generated code [unverified]? Does `espr` fit as the generator base, or does Crucible write its own?
4. **Deterministic profile adoption.** When do Wasmtime and the three browser engines implement the Wasm 3.0 deterministic profile, so the determinizer can drop NaN canonicalization for them?
5. **OSV ecosystem.** Will the OSV project accept a `Crucible` ecosystem name for advisories, and how are correctness advisories represented: as OSV entries with a Crucible-specific database prefix, or in a separate feed?
6. **Foundation.** A new foundation or a project under an existing umbrella organization? The choice decides trademark holding, registry operation and funding.
7. **Marketplace terms.** Fees, refunds, disputes, tax handling, and export control. Some solver packages, catalog parts and designs may fall under export-control regimes [unverified per item], and the registry needs a policy before paid packages open.
8. **ODB++ agreement.** Shared with ELX: the terms under which Crucible may write ODB++ [unverified].
9. **iPadOS distribution.** Does App Review accept Wasm components downloaded from the registry and run by the Pulley interpreter (shared with PLT)?
10. **Test corpora licensing.** The ABC models stay under their creators' copyright and Onshape's terms [ABC]. Is internal testing use permitted, and may derived oracles (hashes, measurements) be published?
11. **Component Model stability.** When does the Component Model binary encoding reach 1.0, and when do all target engines support 64-bit memories in Wasm components?
12. **CVE identifiers.** Should the steward become a CVE Numbering Authority, or request identifiers through an existing one?
13. **Cross-class cache sharing.** Will KLN accept that determinized Wasm component results are independent of `PlatformClass` (CCR-ECO-4)?

## Contract change requests

1. **CCR-ECO-1: Define "External input".** Add to the glossary: *External input: signed, content-addressed data produced outside evaluation (a licensed translation, a supplier offer, a machine reading, an external tool run), pinned in the lockfile and treated by Kiln as a leaf input.* *Reason:* MFG calls such data "signed snapshots", COV a "recorded external Op", and this tab needed a term for licensed translations; the contract and AGT already use "snapshot" for review renders. One concept needs one name.
2. **CCR-ECO-2: Say where licensed translators run.** Section 7 says proprietary formats come "only through licensed translator plugins". Amend to: *licensed translators run as external tools outside evaluation, and their output enters builds only as External inputs.* *Reason:* "plugin" suggests in-process loading, which would break determinism, browser parity and the sandbox (D-ECO-2).
3. **CCR-ECO-3: Evaluation worlds import no WASI.** Section 7 says "Wasm components on WASI 0.3". Amend to: *Wasm components use the Component Model; worlds used during evaluation are synchronous and import no WASI interfaces; tool and connector worlds use WASI 0.3.* *Reason:* determinism, and insulation of the evaluation ABI from the WASI release train (D-ECO-9).
4. **CCR-ECO-4: Cache keys for determinized Wasm components.** Section 5 defines the `Op` cache key with the platform class. Amend to allow, for an `Op` executed by a determinized Wasm component whose host calls are all class-independent, a key without the platform class. *Reason:* determinized Wasm is bit-identical across engines (D-ECO-8, O-ECO-6), so sharing those results across Windows, macOS, Linux and browsers saves recomputation without any loss of determinism.
5. **CCR-ECO-5: Name clearance gate.** Add to phase 0: *trademark clearance for Crucible, Ingot, Anvil, Flux and Kiln in software classes, with fallback names chosen before public launch.* *Reason:* Atlassian sold a code review product named Crucible until May 2025 and supports it until May 2028 [Atlassian Crucible], and Flux (flux.ai) is a PCB design tool in Crucible's own field [Flux AI]. Renaming after launch would cost far more than clearing names now.
6. **CCR-ECO-6: One WIT namespace.** State in section 4 that every first-party WIT package lives under `crucible:`, one package per domain. Rename FLX's `flux:constitutive` and COV's `crucible:material/behaviour` to `crucible:material/constitutive`, and FLX's `flux:solver` to COV's `crucible:physics/solver`. *Reason:* one name per concept (D-ECO-7). FLX and COV still need to settle the merged world's semantics, in particular whether authors supply consistent tangents (FLX) or tangents come from form-level differentiation (COV).
7. **CCR-ECO-7: Packages also hold data.** The glossary defines a package as "containing Ingot source, Wasm components or both". Amend to *Ingot source, Wasm components, data (standards tables, catalog-part definitions, templates, tutorials, themes), or any combination.* *Reason:* MEC ships standards content as data packages, UIX ships themes and tutorials as packages, and catalog-part definitions are data packages (D-ECO-18).

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
