# Interop and ecosystem (ECO)

Interop and ecosystem is everything that crosses Crucible's boundary: translators for other tools' files, sandboxed WebAssembly (Wasm) extensions, the registry that distributes them, the SDKs (software development kits) and connectors around Crucible's API, and the project's licensing and compliance rules. An engineer gets imports that stay live in the design and account for every entity, exports whose bytes reproduce exactly years later, and extensions that behave the same on every system, where incumbents' translators can lose data silently and AI-built clones offer no proof. One mechanism delivers this: every translator and extension is a deterministic, signed package whose output is pinned like any other input, and tools that cannot be deterministic, such as licensed CAD translators, only hand the build signed, pinned files.

## How exchange works

Every product crosses tool boundaries: supplier models come in, manufacturing files go out, and measurements come back. This section follows one part through those crossings and introduces the model the rest of the tab builds on.

ECO owns five things, and the owning tab keeps each piece of domain meaning (MEC for tolerancing, KLN for lifecycle records):

1. **Translation.** The `io/` translators, the translation framework, the format catalog and translator quality.
2. **The Wasm component contract.** Worlds, contexts, capabilities, limits and versioning; PLT owns the determinizer and the runtime (contract section 7.4).
3. **Distribution.** The package registry, catalog-part publishing and the marketplace.
4. **Surfaces around `api`.** SDK packaging, the C application binary interface (ABI), the command-line interface (CLI), events, webhooks and enterprise connectors; AGT owns the method catalog.
5. **Stewardship.** Licensing, governance, disclosure, export and sanctions compliance, trademarks, documentation and migration.

| Term | Meaning |
| --- | --- |
| Translator | A reader or writer for one format family: a Wasm component for open formats, an external tool for licensed ones |
| External tool | A native program run out of process in PLT's sandbox; its output enters builds only as External inputs |
| File | A plain value: name, media type and the SHA-256 of its bytes in the CAS, Crucible's content-addressed store |
| Exchange level | What a format preserves (visual, geometry, structure, semantics or identity), per format and direction |
| Receiver profile | The tolerance and smallest feature that the software receiving an export can represent |

### A worked example: the GP1 bracket

The canonical bracket of contract section 6 is the part of golden product GP1. Three crossings take it from design to a measured article. A small gear motor bolts to its base plate, and the motor's supplier sends a STEP file (ISO 10303, the neutral format for product data). The reference shop machines the bracket from STEP AP242, the application protocol for model-based 3D engineering, with semantic PMI (product and manufacturing information that software can read, not just display), using its own CAM (computer-aided manufacturing) software. An external metrology lab measures the result and returns QIF (Quality Information Framework) results.

```
use std::io::{read, write, step, receivers}

pub feature supplier_motor() -> Assembly {
    let motor = read("assets/gearmotor_rev_c.stp", step::options(pmi: semantic))
    motor.assembly
        .require(motor.report.lost.is_empty(), name: "motor_nothing_lost")
        .require(motor.report.max_deviation < 1um, name: "motor_deviation")
}

pub fn shop_file(p: Part) -> File {
    write(p, step::ap242(pmi: semantic, receiver: receivers::parasolid))
}
```

Read it top to bottom. `read` is an import expression: Kiln evaluates it like any feature and caches the result under the Asset's hash, the options and the translator's version. It returns `Imported { assembly, parts, bodies, report, source }`, and the two checks fail the build if the translator dropped anything or moved geometry by more than a micrometre.

When the supplier sends revision D, the designer changes one path. Kiln re-reads the file, Anvil matches the faces of the two revisions, and the match arrives as a reviewed `import_map`, so the mates and clearance checks on unchanged faces keep working.

`write` turns the released bracket into STEP bytes adapted to the shop's software. The shop's CAM is Parasolid-based, and the receiver profile says such systems treat geometry below 5 nm as coincident. The writer therefore merges or refuses anything smaller instead of sending slivers the CAM would choke on. The same Change produces the same bytes on every machine, so the release tag's hash covers exactly what the shop receives.

The file leaves the organization only as a delivery of the release Act that a person approves, to a recipient record checked at commit. The lab's QIF results come back through a reader that turns each measured characteristic into an Evidence record pinned against the bracket's checks. Had the motor arrived as a SOLIDWORKS assembly, a licensed translator would have run outside evaluation, and the build would read its signed output as an External input.

### Import is a feature

An import that lived outside the program would be a second model with its own state, so imports are ordinary expressions.

**Decision D-ECO-1:** An import is an Ingot expression over an Asset, evaluated by Kiln like any other feature; no imported state exists outside the program.
*Why:* contract principle 2 forbids GUI-only state, and re-importing a supplier's revision D becomes a one-line change with a geometry diff.
*Rejected:* a one-shot native copy, which loses the source; a database of imported objects, which is a second model.

The import statement's `CallSite` comes from source text, so imported names survive a Git round trip.

### Where translators run

| Source | Mechanism | Context | Enters a build |
| --- | --- | --- | --- |
| Open formats | A Wasm component in the `importer` or `exporter` world | Evaluation | As a cached Op output |
| Licensed formats (native CAD, Parasolid, ACIS; JT at first) | An external tool on the vendor SDK, in a translator host under PLT's sandbox | Tool | As a signed External input in `ingot.lock` |
| Live sources (machines, offers, enterprise systems) | A connector Wasm component | Connector | As a signed External input in `ingot.lock` |

**Decision D-ECO-2:** Licensed translators never run inside evaluation; their output enters builds only as External inputs, pinned in the lockfile and signed by the translator host. A clean-room reader built under contract 7.7's insight protocol takes a licensed translator's place once it passes the same qualification.
*Why:* vendor SDKs are native, closed and not bit-reproducible, so pinning their output keeps builds deterministic and lets anyone rebuild without the licence, and a host signature makes the claimed translation verifiable in an audit.
*Rejected:* vendor SDKs during evaluation, which break determinism and the browser; a closed binary in the sandbox, which cannot be audited; unsigned translations, which an auditor cannot tell from substituted geometry.

Each translator host signs every External input it produces with a host key enrolled like a rig runner's, recording the translator version, the licence id and the input's hash. An input without such a signature, such as a translation a user ran on an unenrolled desktop, shows as `Declared` provenance in review.

The translator host runs with network egress denied, which PLT enforces (contract section 7.8). A vendor licence server is a named endpoint that an administrator grants, and a host with that grant receives only inputs at most `internal` without `controls`, unless a two-person grant names it. A tool anyone can re-run, such as an open-source solver in a pinned container, is an External Op instead (contract section 2).

A build that lacks a needed External input fails with `ExternalInputMissing { asset, translator, options }`. The fix, `crucible import assets/gearbox.CATProduct`, runs the tool and records the result in a Proposal, as a translator upgrade does.

[[DIAGRAM diagrams/11-interop-translation-flow.jsx: translation flow · three sources, one evaluation context]]

Read the diagram top to bottom: open formats stay inside evaluation, and licensed or live sources enter it only as signed, pinned External inputs.

### The translation report

A translator that drops data quietly is worse than one that fails, so every read and write returns a `TranslationReport` that checks read and the UI shows beside the model:

| Field | Content |
| --- | --- |
| `entries` | One per source entity: source id (such as `#1234 ADVANCED_FACE`), outcome and target `EntityId` |
| Outcome | `exact`, `approximated(ErrorBound)`, `healed(ErrorBound)`, `merged(into)`, `dropped(reason)` or `unsupported(construct)` |
| `statistics`, `validation` | Counts by category as the CAx Implementor Forum reports them; each declared validation property beside Anvil's value |
| `units`, `max_deviation`, `lost`, `diagnostics` | Conversion; largest deviation; dropped entries; typed errors with fixes, including each healing step |

Five rules govern failure:

1. Every source entity appears in `entries`.
2. Recoverable damage skips and reports the instance; `strict: true` fails on the first error.
3. Healing is explicit: `anvil::heal` records each fix with its bound, and `heal: none` disables it.
4. Validation properties beyond the production thresholds raise a `Warning` check that a design may promote.
5. A writer refuses to drop data: `ExportError` lists what the format cannot carry unless `lossy: allow` is passed.

### Units, axes and identity

Formats that declare units convert to SI with the factor recorded. STL, OBJ and PLY carry no units, so they require `units:`, and omitting it is the compile error `MissingUnits`, whose fix lists plausible readings. Axis conventions become a recorded transform: glTF is Y-up, and an OpenUSD stage declares `upAxis` as Y or Z [OpenUSD up axis].

Anvil names imported entities from the source's persistent id, else from an exact geometric and adjacency signature, never from an ordinal ([ANV, Imported and non-B-rep entities](02-anvil.md#imported-and-non-b-rep-entities)). On a re-import at the same import site, Anvil pairs faces of equal surface type whose parameters agree within the import's healing tolerance and whose adjacency agrees. It writes the pairs as an `import_map` Proposal with a geometry overlay. A face it cannot pair keeps failing with a `ResolveError`, and the reviewer sees exactly which.

### Exports the receiver can use

Anvil resolves features far smaller than most receiving systems can, about 2 nm on GP1. An export that ignores the receiver can therefore carry slivers and gaps that the shop's CAM or CMM (coordinate measuring machine) software treats as broken geometry.

**Decision D-ECO-38:** Every writer of exact geometry names a receiver profile `{ name, tolerance, min_feature }`, and Anvil's `exchange_form` applies it. ECO ships named profiles, starting with `parasolid` at 5 × 10⁻⁹ m, and organizations declare profiles for their own receivers. Entities below `min_feature` merge within tolerance or fail with `NotRepresentable { entities, reason: BelowReceiverResolution }`, and every edge whose tolerance exceeds the profile's is reported. Each procedural face is approximated within the smaller of the profile's tolerance and 1% of the tightest tolerance whose target includes the face. Omitting `receiver:` is `MissingReceiver`, whose fix lists the named profiles.
*Why:* Parasolid's designers chose 5.0e-9 m as a tolerance below that of most real parts [Jackson 1995]. A receiver profile lets the writer refuse what the receiver cannot hold, and tying the approximation bound to the tolerances keeps PMI checks on approximated faces meaningful.
*Rejected:* one global export tolerance, which fits no receiver; leaving slivers to the receiver's healing, which changes geometry outside Crucible's control; a silent default profile, which hides the choice.

MEC's `export_resolution` check runs the profile before any export Act, so a design learns about an unrepresentable sliver in review rather than at the shop.

Writers run in the evaluation context, so an export is a cached Op. Three rules make the bytes stable:

1. Header timestamps, such as STEP's `FILE_NAME` time stamp, come from the time `repo` recorded for the Change.
2. Instance identifiers, such as STEP `#n` numbers, follow the canonical order of `EntityId`s.
3. Floating-point values use the shortest decimal text that reads back to the same binary value.

The signed release tag covers a manifest of exported Files and their SHA-256. Stable bytes let the phase 1 gate release reproduce the run build's AP242 and 3MF (contract section 13.1). Writers derive AP242 persistent ids from `exchange_form`'s id map, and the AP242 writer decides semantic PMI per target face: a control on a facet face exports as presentation only, with a report entry, under MEC's eligibility rule.

Per-recipient watermarks deter casual redistribution and identify unmodified copies only. A watermark is a writer transform keyed with an HMAC (a keyed hash) under the tenant's watermark key, so one recipient cannot forge another's mark, and it never alters definitional geometry or attributes. A recipient who re-saves a STEP file or re-slices a 3MF removes it, so traceability rests on the release-data record of who received which file hash ([KLN, Exits](05-kiln-repo-plm.md#exits)).

### Untrusted content in imported files

An imported file comes from outside the organization, so it can attack the parser, the agents that read it and the people who look at it:

1. **Hostile bytes.** Parsers run with fuel, memory and output limits, and every reader is fuzzed continuously.
2. **Hostile text.** Names, notes, PMI text and metadata come back as `ExternalText` with origin (AGT), and entities get neutral identifiers such as `part_017`.
3. **Hostile appearance.** Readers mark every output of an Asset `data_untrusted`, and Kiln joins it into everything derived. A human merge of the import Proposal endorses its typed outputs (contract section 5.3), while its text stays `ExternalText`. A render of an unendorsed Body is instruction-capable, since geometry can depict text.

Archives (3MF, USDZ, Functional Mock-up Unit (FMU) packaged simulation models, SSP system descriptions) are read with limits on entries, expanded size and compression ratio, and a path outside the root fails with `ImportError::UnsafeArchivePath`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `read(path, options) -> Imported` | Pinned Asset to core types, report and header | `ImportError` with a fix | ECO-O-1, ECO-O-17 | 1 |
| `write(model, format, options) -> File` | `Body`, `Part`, `Assembly` or `Field` to a File in the CAS | `ExportError` listing what cannot be carried | ECO-O-3, ECO-O-4 | 1 |
| `probe(path) -> FormatInfo` | Format, schema and edition from the first 4 KiB | `Unknown` with the closest matches | ECO-O-16 | 1 |
| Licensed translation | External tool without egress; output pinned and signed by an enrolled host | `ExternalInputMissing`; unsigned inputs shown as `Declared` | ECO-O-8, ECO-O-15 | 2 |
| Translation report | Every source entity accounted for | A missing entry blocks release | ECO-O-17 | 1 |
| Units and axes | Recorded conversion; `units:` for unitless formats | `MissingUnits` with plausible readings | ECO-O-16 | 1 |
| Imported identity and matching | Persistent ids or exact signatures; re-imports matched into a reviewed `import_map`. Requires: ANV Imported entity ids; ANV `anvil::match_bodies` | `NoCorrespondence { faces }`; unpaired faces keep their `ResolveError` | ANV-O-NAME-4 | 1 |
| Receiver profiles | Named and declared profiles; merges, refusals and tolerant-edge reports | `MissingReceiver`; `NotRepresentable { entities, reason: BelowReceiverResolution }` | ECO-O-35 | 1 |
| Exchange form | Seams, poles, B-spline approximations within the receiver's bound, id map | `NotRepresentable { entities, reason }` (ANV). Requires: ANV `anvil::exchange_form` | ANV-O-NF-1, ECO-O-24 | 1 |
| Deterministic export | Byte-identical Files everywhere | None: a writer is a pure function of the Change, and ECO-O-4 catches any divergence | ECO-O-4 | 1 |
| Recipient watermarking | HMAC-keyed, non-definitional, recorded with the release data | `WatermarkUnsupported { format }` | ECO-O-33 | 3 |
| Untrusted content | Limits, `ExternalText`, integrity until endorsed | `ImportError::LimitExceeded`; `ImportError::UnsafeArchivePath` | ECO-O-5, ECO-O-18 | 1 |

## Formats and exchange levels

No single format carries a whole product, so each domain's standards get translators with a stated promise of what they keep. This section sets how each format is built, the levels a format can preserve, and the decisions behind the harder rows; the full catalog is in [Reference](#format-catalog).

Every format gets one strategy:

- **Build:** a Rust Wasm component, generated from a schema where one exists (EXPRESS for STEP and IFC, XSD for XML).
- **Wrap:** a mature open library under a compatible licence, compiled to a Wasm component.
- **Adopt:** a permissive or MPL-2.0 (Mozilla Public License) Rust library on contract 7.7's adopt list, linked after a provenance audit.
- **License:** a commercial SDK as an external tool (D-ECO-2), until a clean-room reader built under contract 7.7's insight protocol passes the same qualification.

**Decision D-ECO-3:** Open formats are built in Rust as Wasm components and run in the evaluation context on every platform. Each STEP and IFC translator has three layers with separate oracles. Layer 1 is a Part 21 reader and writer generated from EXPRESS, with late-bound access for AP242's long tail. Layer 2 holds generated rule checkers, and layer 3 holds hand-written mappings per protocol and per practice of the CAx Implementor Forum (CAx-IF), the phase 1 critical path.
*Why:* every platform runs the same translator and Anvil alone interprets geometry, while most of a STEP translator is mapping, which EXPRESS does not encode.
*Rejected:* wrapping Open CASCADE (LGPL-2.1 with an exception [OCCT licence]), which serves as a differential oracle instead; per-platform native libraries, which break parity; early-bound types for all of AP242, which bloat the component.

**Decision D-ECO-33:** The repository never vendors ISO schema files: the generator fetches the EXPRESS schemas from ISO's portal by pinned hash, and generated Rust holds only entity and attribute names and types. The steward asks ISO, through ISO/TC 184/SC 4, for written permission to distribute that code under Apache-2.0 as a phase 0 gate item. If ISO refuses, the steward publishes the generator and the expected binary hash for each pinned schema hash. Any holder of the schema then generates bit-identical layer 1, which the host accepts only at that hash, and desktops generate it locally from the user's copy.
*Why:* ISO permits its electronic inserts only "in their original format without any modifications" [ISO 10303 portal], and a deterministic fallback keeps every `NodeKey`, cache entry and open-source build identical whichever way ISO answers.
*Rejected:* vendoring the schemas, outside the permission; a hand-written AP242 model, which gives up generation; a per-organization build loaded from its team server, which splits caches and leaves desktops without a server unable to read STEP.

`espr`, an Apache-2.0 EXPRESS compiler for Rust, has had no release since 0.4.0 on 20 September 2024 [espr crates.io]. Crucible forks its parser into `io/` and owns the generator.

| Exchange level | Preserved | Example |
| --- | --- | --- |
| Visual | Tessellation, appearance, names | glTF export, OBJ |
| Geometry | Exact B-rep, or a mesh with a stated `ErrorBound` | IGES read, STL |
| Structure | Assemblies, Instances, placements, Part identity, properties, materials by name | AP214 read |
| Semantics | Semantic PMI, kinematics, composites, FE models, connectivity, toolpaths | AP242 with PMI, IPC-2581, QIF |
| Identity | Persistent ids that survive a round trip | AP242 persistent ids, IFC GlobalIds |

Levels are cumulative. A catalog version "at phase n" is fixed in the row's conformance suite (ECO-O-16) when that phase opens, and every row shares `read`, `write` and `probe` at its level.

Phase 1 carries what GP1 and GP2 need plus the parity floor (contract 13.4): STEP AP242 with semantic PMI write, AP203 and AP214 read, IGES read, STL, 3MF with beam lattices, drawing sheets as PDF, SVG, PDF/A and DXF, and QIF results. Licensed native CAD, full DXF and DWG, board exchange and AP242 PMI read follow in phase 2. The phase 0 freedom-to-operate search covers the AP242 and 3MF writers, and each later gate's search covers that phase's new translators (contract section 13.1). Apart from DWG, Crucible never writes native proprietary CAD formats: exchange back uses AP242 with persistent ids, which the CAx-IF tests as "ping-pong" iteration [CAx-IF 58J], or licensed Parasolid and JT.

**Decision D-ECO-4:** Formats built on HDF5 (CGNS, Exodus II, VTKHDF) wrap the reference C libraries compiled to Wasm components, with `H5Pset_obj_track_times` switched off [HDF5 track times] and ECO-O-4 proving the bytes stable.
*Why:* HDF5's reference library is its only complete implementation.
*Rejected:* a pure Rust HDF5 subset, revisited only if the library blocks determinism; native libraries, which break browser parity.

### Drawings in DXF and DWG

Shops quote, cut and archive from DXF and DWG every day, and a drafting user expects to open a supplier's DWG and edit it.

**Decision D-ECO-39:** The DXF writer for drawing sheets and planar sections ships in phase 1. DXF and DWG read and write, R12 to R2018, ship in phase 2 through acadrust, linked under MPL-2.0 after the verifier's provenance audit. If the audit fails, ECO builds its own codec from the Open Design Alliance's published DWG specification, with acadrust and LibreDWG as oracles. A licensed translator serves only DWG versions outside that range. An imported DWG becomes an editable drawing program through an import expression, as a 3D Asset does, and MEC owns what a 2D-only drawing holds.
*Why:* acadrust reads and writes DXF and DWG from R12 through R2018 under MPL-2.0 [acadrust], which contract 7.7 allows to link, and an AI-built AutoCAD clone already opens and saves DWG through it [CADCraft].
*Rejected:* DWG only through a licensed translator, which leaves the commonest shop format behind a fee in phase 3; linking LibreDWG, which is GPL-3.0; DXF only, which loses the files customers actually send.

### Simulation decks and system models

Analysts carry years of validated Nastran and Abaqus models and Modelica libraries, and Crucible earns their trust only if those run, not merely display.

**Decision D-ECO-40:** In phase 3, ECO reads Nastran bulk data and OP2 results, Abaqus input and LS-DYNA keyword decks (meshes, parts, materials and contacts). It writes a study as Nastran bulk data (SOL 101, 103, 111 and 112) and Craig–Bampton reductions as DMIG and OP4. A read deck becomes a `Mesh` Body plus a study whose cards FLX maps to its forms and idealizations. A card FLX cannot map fails with `UnmappedCard { card, line }` and is never dropped, and the route stays `Unverified` per card family until its oracle passes.
*Why:* users of commercial tools expect deck export with idealizations, as Ansys documents for SOL 101, 103 and 109 with RBE2, RBE3, CBUSH and CONM2 [Ansys Nastran export]. An incumbent re-running Crucible's model is also the strongest check a customer can make.
*Rejected:* view-only decks, which strand validated models; silently dropping unmapped cards, which changes the model; a vendor solver as the only reader, which needs a licence.

**Decision D-ECO-41:** A Modelica reader translates a declared subset of Modelica source (equation sections, connectors with flow and stream variables, `inner` and `outer`, records, replaceable classes) into `network { … }` Ingot in phase 4. It is an `io/` Wasm component built on Rumoca or a clean-room parser; a construct outside the subset keeps the model as an FMU with `Untranslated { construct }`.
*Why:* Modelica users bring source libraries, Dymola builds on the language and its domain libraries [Dymola], and the Network compiler already holds the equation machinery, so only a front end is missing; Rumoca is an Apache-2.0 Modelica compiler written in Rust [Rumoca].
*Rejected:* FMUs only, which cannot be edited, diffed or differentiated in Crucible; a full Modelica compiler before GP6, which no gate needs.

ELX states the translation coverage as a share of the Modelica Standard Library's example models, a BSD-3-Clause library spanning mechanical, electrical, magnetic, thermal and fluid components [MSL].

### Machine definitions

A machine package needs the machine's kinematic structure, and machine builders rarely publish open kinematic models, so ECO reads only sources whose terms are recorded. A builder's STEP model is read as a structure Asset with its `geometry_licence` recorded, as for catalog parts. Axis and controller parameters come from MTConnect device models and controller connectors as External inputs. Machine definitions from CAM or verification vendors enter only through a vendor export the organization licenses, with the licence id recorded. MFG owns the machine package and its checks; the catalog lists each source in [Machine-definition sources](#machine-definition-sources).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| STEP layer 1: Part 21 | Generated reader and writer; hash-pinned schemas; deterministic fallback build | `ImportError::Unreadable { location }` | ECO-O-23, ECO-O-5 | 1 |
| STEP layer 2: schema rules | Generated checkers on every export | `ExportError::SchemaRule { rule, instance }` | ECO-O-3 | 1 |
| STEP layer 3: AP242 mapping | Geometry, structure, properties, PMI write | Report entries | ECO-O-1, ECO-O-2 | 1 |
| AP242 PMI read, persistent ids, tessellation | Per recommended practice | Report entries | ECO-O-2, ECO-O-24 | 2 |
| IGES read | Geometry level, healed with bounds | `ImportError` naming the entity | ECO-O-16 | 1 |
| 3MF and STL | Beam Lattice marked required; a Core mesh beside it | `ExportError` over the triangle budget | ECO-O-16 | 1 |
| Inspection results import | QIF Results or CSV to one Evidence record per characteristic (MFG) | Unmatched labels reported. Requires: MFG Results as Evidence records | ECO-O-16 | 1 |
| Drawing writers | PDF, SVG, PDF/A and DXF of sheets and planar sections | `ExportError` | ECO-O-3, ECO-O-4 | 1 |
| DXF and DWG exchange | Read and write R12 to R2018; imported DWG as an editable drawing program | `ImportError::UnsupportedVersion { version }` with the licensed fallback | ECO-O-36 | 2 |
| Licensed MCAD translators | Mechanical catalog rows | Unqualified versions flagged | ECO-O-15 | 2 |
| Board exchange for mechanical teams | IDF, STEP boards and IDX to a read-only board Part | `ImportError` naming missing data | ECO-O-26 | 2 |
| Board fabrication and assembly writers | Gerber, XNC, IPC-2581C, ODB++, IPC-D-356, placements | `ExportError` | ECO-O-25 | 3 |
| Solver decks | Nastran, Abaqus and LS-DYNA read; Nastran, DMIG and OP4 write | `UnmappedCard { card, line }`. Requires: FLX Imported solver decks; FLX Solver deck export | ECO-O-37 | 3 |
| Modelica source import | Declared subset to Networks; FMU fallback | `Untranslated { construct }` | ECO-O-38 | 4 |
| Machine definitions | Builder STEP, MTConnect device models and licensed vendor exports, each with its licence recorded | `ImportError::LicenceUnrecorded { source }` | ECO-O-16, ECO-O-31 | 2 |
| IDX change proposals | Incremental exchange with responses | Rejected proposals reported | ECO-O-16 | 4 |
| HDF5-based formats | Wrapped library, deterministic writes | `ExportError::Nondeterministic` | ECO-O-4 | 4 |
| Remaining catalog rows | Per catalog row | Report rules | ECO-O-16 | 2 to 5 per row |

## Translator quality

A translator ships only when independent oracles show it keeps its catalog row's promise, because a wrong translation is a design error that nobody typed. Five layers do this: interoperability testing, validation properties, round trips, differential testing and fuzzing.

### CAx-IF participation

The CAx Implementor Forum (CAx-IF) belongs to the MBx Interoperability Forum of AFNeT, PDES, Inc. and prostep ivip [MBx-IF]. Round 58J ran from March to September 2026 and covered assembly PMI, composites, kinematics, persistent ids, holes and threads [CAx-IF 58J].

**Decision D-ECO-5:** Crucible joins the MBx Interoperability Forum in phase 1 and takes part in every CAx-IF round, and each round's results become regression oracles.
*Why:* the forum is where AP242 implementers agree on practices and find each other's bugs against real CATIA, NX and Creo output.
*Rejected:* public sample files alone, which miss current practices; waiting for a mature translator, which delays the bugs that matter.

Round files enter `oracles/` only where the forum's terms allow; otherwise only Crucible's own results do. The fee is a phase 1 budget line that the founder approves at the phase 0 gate.

### Validation properties and corpora

In the CAx-IF practice, version 4.6, a sender writes validation properties so a receiver can check what it read [CAx-IF GVP]:

| Property | Interoperability testing (green / yellow / red) | Industry production |
| --- | --- | --- |
| Volume, area, curve length | Below 1% / 1–10% / above 10% | 0.5% |
| Centroid | Below 1 mm / 1–5 mm / above 5 mm, or 0.1% / 1% of the box diagonal | 0.02 mm plus 0.1% for models over 20 mm |
| Bounding box | Absolute error of both corners | 0.5% |

Exports write these properties from Anvil's certified integration, and imports check them against the production thresholds. The internal target is 0.05% on volume and area. Round trips and item-by-item PMI comparison cover what properties miss.

**Decision D-ECO-37:** Oracles never vendor third-party datasets: each corpus is a list of content hashes fetched at test time, with a licence proof per item. ABC enters only as contract section 13.3's licence-filtered subset: documents that show, through the Onshape API, a Free Plan owner, creation on or after 7 August 2018 and no LICENSE tab. The subset serves benchmarks and published measurements, and AGT's training rule governs any training use.
*Why:* ABC's models belong to their creators [ABC], and Onshape licenses copying only for those documents [Onshape terms].
*Rejected:* all of ABC "for testing only", since copying is itself a use; vendored corpora, which ship with the repository; the Fusion 360 Gallery dataset, which is non-commercial only [Fusion 360 Gallery licence].

| Corpus | Contents | Access |
| --- | --- | --- |
| NIST MBE PMI test cases | CTC, FTC, STC and HTC files with native models [NIST MBE PMI] | Public |
| CAx-IF round files | Current-practice files from many systems | Participants, under the forum's terms |
| ABC licence-filtered subset | Onshape models with STEP, Parasolid, meshes and FeatureScript | Hash list with a licence proof per model |
| Held-out corpus; format suites | Models never shown to agents; 3MF, FMU, SSP, IFC, KiCad, DWG and solver-deck samples | Protected store; hash lists |

### Round trips, fuzzing and qualification

All topology comparisons use Anvil's topology normal form on both sides (ANV-O-NF-1).

| Suite | Pass line | Phase |
| --- | --- | --- |
| Self round trip | Exact geometry bit-identical, procedural within its stored bound; topology equal; ids and PMI kept | 1 |
| External round trip on CAx-IF ping-pong cases | Properties within thresholds; persistent ids match; edits appear as a diff | 2 |
| Differential read against Open CASCADE 8.0.1 [OCCT releases], later a licensed translator | Topology equal; Hausdorff distance under the larger tolerance; disagreements triaged | 1 |
| Independent readers for other formats | lib3mf for 3MF; LibreDWG for DWG; pyNastran and meshio for solver decks; each run only as an oracle | 1 to 3 per format |

Open CASCADE, LibreDWG and the other copyleft readers run only as external oracles in CI. Readers are fuzzed with structure-aware mutators and grammar-based generators, and each release needs 10⁹ executions per reader without a new crash (target).

A licensed translator version is qualified on the NIST and held-out native files before anyone can pin it. A signed record keeps its topology counts, property deviations and PMI statistics, shown beside every External input it produced. Translators are versioned packages, so output changes are labelled (D-ECO-14).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| CAx-IF participation | Every round; results become oracles | A regression blocks release | ECO-O-1, ECO-O-2 | 1 |
| Validation properties | Written and checked | `Warning` check beyond thresholds | ECO-O-1 | 1 |
| Corpora by hash list | No vendored third-party data; a licence proof per item | An item without a licence proof is not fetched | ECO-O-31 | 0 |
| Round trips in normal form | The suites above | A self round-trip failure blocks release | ECO-O-24 | 1, 2 (external) |
| Reader fuzzing | Continuous, per reader | A new crash blocks release | ECO-O-5 | 1 |
| Licensed translator qualification | Signed record per version | Unqualified versions cannot be pinned | ECO-O-15 | 2 |
| Translator versioning | Output changes labelled; pins re-export identically | Unlabelled changes refused | ECO-O-10, ECO-O-22 | 1 |

## The extension model

Anyone, Crucible's own builders included, extends Crucible through the same public mechanisms (contract principle 1), so the contract an extension runs under decides what a stranger's code can do to a design. This section fixes where extensions run, what they may reach and how they stay deterministic.

### Tiers and contexts

Contract section 4 fixes three tiers: Ingot packages, Wasm components and operations. Wasm components carry importers, nesting, toolpath strategies, specialist solvers, panels and connectors, and anyone contributes an operation through the public RFC (request for comments) process.

**Decision D-ECO-6:** Authors choose the tier by a fixed rule. A Wasm component is used only when code needs over about 10⁶ primitive steps per call, an existing codebase, or a data structure Ingot handles poorly. An operation is used only when three independent packages need it, it needs GPU or SIMD kernels, or it must be differentiable through Flux.
*Why:* most logic stays in the most reviewable tier.
*Rejected:* free choice, which misplaces heavy and trivial code; a native plugin tier, unsafe and absent from browsers.

Process isolation of third-party Wasm components is the one difference principle 1 permits; PLT's call-overhead targets and the batched `crucible:ops` form bound it (contract section 7.4). A Rust `#[ingot::feature]` receives ING's guest context, `ingot_sdk::Cx`, and the native `OpCx` never enters a Wasm component. Wasm components are CPU-only: GPU work lives in operations, which they call through `crucible:ops`.

A component's context decides what it may import:

| Context | Runs | May import | Never imports | Output enters |
| --- | --- | --- | --- | --- |
| Evaluation | Inside Kiln as an Op | `crucible:ops`, `geom`, `field`, `product`, `host`, type-only interfaces | `wasi:`, `crucible:api` | Kiln, under the node's key |
| Panel | Out of process if third-party | `crucible:api/read`; `edit` when granted | Clocks, randomness, files, network | `api` calls recorded in `ChangeProvenance` |
| Tool | In `apps/tool-runner` | `crucible:api`, `wasi:filesystem` on granted directories, `wasi:clocks`, `wasi:random`, `crucible:tool/process` | Network, except granted endpoints | External inputs, `api` calls |
| Connector | On a team server or desktop | Scoped `crucible:api`, `wasi:http` to declared hosts, `wasi:clocks`, `wasi:random`, `crucible:connect` | Files, processes | External inputs, events, Acts |

The registry checks imports at publish and the host again at instantiation. An evaluation component reaches engine data only through `crucible:ops` and `crucible:host/cas` reads of objects reachable from its input handles (contract section 4). A raw `ObjectId` resolves to nothing, every read joins the node's label, and measurements are operations, never host calls.

Processes spawned through `crucible:tool/process` run in PLT's sandbox with egress denied (contract section 7.8). A manifest may declare named endpoints, such as a licence server, which an administrator grants and the sandbox enforces by address.

### Isolation and platforms

**Decision D-ECO-26:** Only first-party Wasm components from the hermetic builder run inside the engine process. Every third-party one, a user's unpublished one included, runs in a worker under PLT's OS sandbox that holds no tokens, handles or keys. On servers, workers are per tenant and confidentiality label, labels with `controls` get dedicated VMs, and pooling slots never cross them. Trusted builders run third-party code only in single-use microVMs (contract section 7.8).
*Why:* the engine process holds every open repository, token and device key. Isolation bugs in the runtime itself are real, as Wasmtime's April 2026 advisory on a pooling-allocator data leak shows [Wasmtime GHSA-6wgr].
*Rejected:* in-process execution for verified publishers, since identity is not memory safety; one worker pool for all tenants, which an escape would cross.

PLT applies Wasmtime security releases within 7 days, each gated by ECO-O-6; the same month's string-transcoding advisory was an out-of-bounds write [Wasmtime GHSA-394w].

| Platform | Engine |
| --- | --- |
| Windows, macOS, Linux; servers | Wasmtime LTS with Cranelift in `wasm-host` (PLT) |
| Desktop browsers | The browser's engine through one first-party Wasm component runtime (D-ECO-10) |
| iPadOS | The web build in a WKWebView shell, where JavaScriptCore compiles Wasm; only first-party components in the app run locally (contract section 7.4) |
| Android tablets | Wasmtime, Tier 3 there [Wasmtime tiers]; Play allows downloaded code only with indirect API access [Google Play DNA], so no world imports an Android API |

Tool and connector components run on the server for browsers and tablets. On iPadOS no downloaded code runs (guideline 2.5.2), and packages appear only as design dependencies under guideline 3.2.2(i) [App Review]. Local registry components there would first need a 4.7.4 web index, 4.7.1 reporting and 4.7.5 age ratings.

**Decision D-ECO-10:** The registry ships determinized core modules plus a data description of each Wasm component, never per-component JavaScript, and one first-party browser runtime lifts and lowers from it. Browsers evaluate third-party evaluation components remotely until the asynchronous bridge passes PLT-O-WASM-1, PLT-O-WASM-6 and PLT-O-WASM-7 there ([PLT, Isolation of third-party Wasm components](12-platform-performance.md#isolation-of-third-party-wasm-components)). Then each runs in PLT's browser sandbox, and only after ECO-O-8's exfiltration cases pass in that engine.
*Why:* generated glue would run beside every local repository and key.
*Rejected:* per-component ES modules as jco generates them [jco]; transpiling in the client; Pulley compiled to Wasm.

PLT owns the web app's integrity (an asset manifest in a transparency log, checks by TUF (The Update Framework) in the service worker, expiring apt and dnf metadata) and the main origin's own content policy.

### WIT packages

Every interface a Wasm component sees is a WIT (WebAssembly Interface Types) package, so the WIT packages are the extension contract.

**Decision D-ECO-7:** Every first-party WIT package uses the `crucible:` namespace, one package per domain, in American spelling. Operations are reached only through `crucible:ops`, with one generated interface per catalog; `crucible:geom` and `crucible:field` hold types and builders, and product structure lives in `crucible:product`.
*Why:* one namespace makes ownership obvious, any other computing interface would bypass recorded Op dependencies, and "model" names a physics model elsewhere.
*Rejected:* per-subsystem namespaces such as `flux:`; operations inside `crucible:geom`; `measure` and `sample` host interfaces; the name `crucible:model`.

Each package follows SemVer [WIT guide], and its owner specifies it with an oracle that the published WIT matches; [Reference](#wit-package-index) holds the index and ECO's own packages. WIT forbids recursive types [WIT gates], so trees cross as arenas: flat lists in pre-order with each node's parent as an index, as `crucible:ui` does for panel trees. No `crucible:` package freezes before the names clear (contract section 13.1), and examples use `@0.1.0` until then. Units cross as SI `f64` while the Ingot wrapper carries `Quantity<D>`, and strings a component authors become `ExternalText`.

### Capabilities

A Wasm component can call only what its world imports. The manifest scopes each import (hosts, directories, `api` scopes, named secrets), a person grants each scope per package, and `ingot.lock` records it. Organization policy allows or denies publishers, capabilities and licences, and evaluation components need no grants.

**Decision D-ECO-27:** A Wasm component may hold at most one of three capabilities (reads above `public`, network egress, and file writes outside the CAS), and only a `policy:admin` grants an exception. Connector `api` scopes never include design reads, outbound data from labelled reads goes through a `release_data` Act, and grant screens state combinations, such as "can read your designs and send data to api.supplier.com".
*Why:* two harmless-looking grants combine into an exfiltration channel.
*Rejected:* per-capability grants without a flow rule; taint tracking inside components, which the sandbox cannot verify.

An update that adds a capability or changes the signer waits as a Proposal. A named secret goes only to its declared host, revoking a grant stops running instances with `CapabilityDenied { capability, package, fix }`, and every tool and connector call is audited.

### Determinism and limits

Contract section 7.4 states the rules, and PLT owns the determinizer and its overhead table. ECO adds three:

1. Randomness arrives only as an explicit `seed` argument from an Ingot `Rng` (ING).
2. Limit outcomes follow KLN's one catalog: `kiln/fuel_exhausted`, `kiln/stack_exhausted`, `kiln/work_limit` and `kiln/memory_limit` are cached `Failure`s whichever layer reaches them (contract 7.2), and host resource errors and cancellation are Aborts.
3. Data parallelism uses `crucible:host/parallel`, whose combinators return outputs in input order; KLN owns the `crucible:host` package and PLT implements `parallel` behind it.

**Decision D-ECO-8:** Evaluation-context Wasm components execute only as determinized binaries. The registry runs PLT's determinizer at publish in a single-use microVM that runs no package code, twice on different hosts, and each host computes the output hash; the index entry records both receipts. The local toolchain runs the same version for unpublished components, and every host re-runs it on the published input at install and refuses a mismatch. The binary's SHA-256 enters the `NodeKey`.
*Why:* engine-independent instrumentation gives identical results and trap points everywhere, as `wasm-instrument` shows for metering [wasm-instrument]. A determinizer that shared a worker with the package's own tests could be handed an uninstrumented binary to sign.
*Rejected:* engine fuel, absent from browsers; wall-clock timeouts, which are nondeterministic; instrumenting on each client without a published reference, a second producer of executed bytes; determinizing on the untrusted-evaluation workers that run the package's test vectors.

**Decision D-ECO-9:** Evaluation worlds import no WASI and are deterministic. Their `crucible:ops` imports are Component Model async functions in the callback ABI (contract section 7.4), so a host may answer across a process or agent-cluster boundary. The host delivers completions in issue order and fuel never counts host time. Evaluation worlds use no `stream` or `future` types, while tool and connector worlds use WASI 0.3's [WASI 0.3].
*Why:* third-party components run out of process, and the callback ABI returns to an event loop without fibers [CM concurrency].
*Rejected:* synchronous evaluation worlds, which browsers cannot answer across agent clusters; the stackful ABI, which needs stack switching; free completion order, which is nondeterministic.

Limits apply per call. A manifest may request more, up to the organization's ceiling, and PLT's limiter reserves budget as memory grows.

| Limit | Evaluation default (ceiling) | Tool and connector default | Outcome |
| --- | --- | --- | --- |
| Linear memory | 256 MiB (4 GiB) | 2 GiB | `memory.grow` past the declared maximum is the cached `Failure` `kiln/memory_limit { limit }` (contract 7.2); a host-caused failure below it is a `ResourceExhausted` Abort |
| Fuel | 5 × 10¹⁰ units, roughly 10 to 30 s native (policy) | Wall-clock budget | `kiln/fuel_exhausted { used, limit }`, cached |
| Logical stack | 256 KiB (1 MiB, calibrated in phase 0) | Engine default | `kiln/stack_exhausted { limit }`, cached |
| Output; handles; binary | 2 GiB per output; 10⁷ handles (10⁸); 64 MiB (256 MiB) | Policy; 10⁶; 64 MiB | `kiln/work_limit { kind, limit }`; large binaries refused at publish |
| Wall clock | None, cancellation only | 15 min per call | The call fails with `Timeout`, never cached |

Work above 4 GiB uses PLT's chunked buffers, operations or server-side tool components. 64-bit memories stay off until every Tier 1 browser engine supports them [Wasm 3.0].

### Versioning

An extension pinned in a released design must keep running for the product's life, so WIT packages follow SemVer with feature gates: `@since` items never change incompatibly, `@unstable` items may vanish, and `@deprecated` pairs with another gate [WIT gates]. Five rules follow:

1. A 1.x package only adds items; unstable features are opt-in and publish only in pre-releases.
2. Deprecation lasts at least 24 months and one edition, and a new major ships an adapter for the old world.
3. Every world major stays executable for 10 years after it is superseded (target).
4. No engine upgrade ships unless every registry test vector's hash is unchanged.
5. If the Component Model's binary encoding changes [Component Model], the registry re-encodes stored components, proves identical results and keeps the original hash as identity.

WASI 0.3.0 shipped on 11 June 2026 and 0.3.1 on 11 August 2026, with no date for 1.0 [WASI roadmap]. Wasmtime 46 first implements final 0.3.0 [WASI 0.3], and only tool and connector components track this train, on the current and previous 0.3.x releases.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Contexts and worlds | Imports checked at publish and instantiation | `ForbiddenImport { import, fix }` | ECO-O-8 | 0 |
| First-party WIT packages | Index; 0.x until names clear; arena trees, no recursive types | Unstable items need opt-in; an unparseable package fails release | ECO-O-6, ECO-O-34 | 0 |
| ECO's WIT packages | `units`, `io`, `tool`, `connect` as tabled in Reference | A differing interface fails release | ECO-O-34 | 0 (`units`), 1 (`io`), 2 |
| `crucible:ops` bindings | Generated async interfaces with a batched form | `OpVersionRetired` with an upgrade | ECO-O-6 | 1 (`anvil`), 2 (`flux`) |
| Data access by handle | `crucible:host/cas` reads only objects reachable from input handles | A raw `ObjectId` resolves to nothing | ECO-O-8 | 1 |
| Process isolation | Sandboxed workers; microVMs on trusted builders | Worker loss is an Abort | ECO-O-8 | 1 |
| Tool egress | No network; named endpoints by grant (PLT enforces) | `EgressDenied { host }` | ECO-O-8 | 1 |
| Capability grants and flow rule | Scoped grants; at most one risky capability | `CapabilityDenied` | ECO-O-8 | 1 |
| Determinized execution and limits | Code-free determinizer runs on two hosts; install-time re-run; seeds; KLN's outcomes | Limit `Failure`s cached; a hash mismatch refuses the component | ECO-O-6, ECO-O-7 | 0; 1 (install-time re-run) |
| Browser Wasm component runtime | Generic runtime for first-party components | Missing description fetched remotely | ECO-O-6 | 1 |
| Browser sandbox | Remote until the bridge and the exfiltration cases pass per engine, then the sandboxed iframe and worker | Remote evaluation | ECO-O-8 | 2 |
| Tablet execution | First-party components only on iPadOS | Remote evaluation | ECO-O-6 | 3 |
| WIT versioning | Additive minors, deprecation, adapters, retention | A removal in a minor is refused | ECO-O-10 | 0 |

## SDKs, CLI, events and connectors

AGT's method catalog is the only programmatic surface, and people reach it from many languages, CI systems and enterprise systems; this section packages it and adds the events, exit surfaces and connectors around it.

### SDKs and the CLI

| SDK | Form and distribution | Phase |
| --- | --- | --- |
| Rust | `sdk/rust`: `api` types with HTTP and in-process clients | 0 |
| Python | `sdk/python`: pure Python generated from the catalog's JSON Schemas, with PEP 740 attestations [PEP 740] | 1 |
| TypeScript | `sdk/typescript`: pure TypeScript for Node.js, Deno, Bun and browsers, through trusted publishing [npm security plan] | 2 |
| C ABI | `sdk/c`: `libcrucible` for C, C++, C#, Java, Julia, MATLAB and CAD add-ins; archives per Tier 1 target | 2 |

Every index publishes the SDK as `crucible-sdk`, since unrelated projects hold `crucible` on PyPI [PyPI crucible] and on crates.io [crates.io crucible]. The name is free on crates.io, PyPI and npm, and ECO reserves it on every index at the phase 0 name gate.

**Decision D-ECO-11:** The official SDKs are Rust, Python, TypeScript and a C ABI; other languages bind the C ABI or generate a client from the JSON Schemas and OpenAPI 3.1 description.
*Why:* these four cover systems code, scripting, web, agents and every foreign-function interface, and each extra SDK multiplies parity testing.
*Rejected:* official Java, C# and Julia SDKs; a Python SDK on native extensions, since AGT keeps SDKs pure-language.

SDK versions equal the catalog version. A method is deprecated for at least 12 months before a major removes it, and servers serve the previous major for 24 months.

The C ABI passes canonical JSON through `crucible_call`, streams Evaluations through `crucible_call_stream` and maps CAS objects with `crucible_cas_map`. Handles are opaque, panics never cross it, and removing a symbol needs a new library name.

Every method is `<group>.<name>` in the contract's eight groups, and error codes take the separate form `<family>/<code>` (contract section 7.6). AGT's catalog holds ECO's methods, listed in [Reference](#api-methods-and-cli). Publishing, yanking and every export are Act kinds.

The `crucible` CLI maps subcommands one to one onto methods, with aliases for daily work, and `crucible update parts` lists every substitution a `CatalogSelection` makes. Output is text or canonical JSON (`--json`), exit codes are stable, and `--offline` turns any network need into a typed error.

### Events and webhooks

Build pipelines, business systems and chat tools react to what happens in Crucible, so every tab's events share one envelope and one delivery mechanism.

**Decision D-ECO-12:** ECO owns the event envelope, delivery and signing for every tab. Events use CloudEvents 1.0, and webhooks follow Standard Webhooks, signed with Ed25519 (`v1a`) by default. Payloads are thin (ids, opaque references and a link, never design content), and KLN's sequence number travels zero-padded in the `sequence` attribute [CloudEvents sequence].
*Why:* both are open specifications with receiver libraries, and asymmetric signatures leave receivers no forging secret.
*Rejected:* a custom envelope; HMAC-only signing; fat payloads, which bypass access control; per-tab envelopes.

CloudEvents requires `id`, `source`, `specversion` and `type`, with `source` plus `id` unique [CloudEvents]. `source` is the repository, registry or catalog URI, and `type` takes a reverse-DNS prefix from the steward's domain once the name gate fixes it. KLN defines repository, lifecycle and evaluation types, AGT the Act types, and ECO registry and catalog types such as `package.yanked` and `part.lifecycle_changed`.

1. **Pull.** `read.events` returns events in per-source order, retained at least 30 days (target); CI uses this path.
2. **Push.** Deliveries carry `webhook-id`, `webhook-timestamp` and `webhook-signature`; HMAC-SHA256 (`v1`) serves receivers that cannot verify Ed25519 [Standard Webhooks spec]. Receivers reject timestamps over 5 minutes old.
3. **At least once.** Receivers deduplicate by `webhook-id`, and retries back off with jitter over about three days, then go to a dead-letter queue.
4. **Address rules.** Deliveries leave through PLT's egress proxy, which checks each resolved address at connect time against ECO's webhook rules: loopback, private, link-local, carrier-grade NAT (100.64.0.0/10), IPv6 unique-local and IPv4-mapped ranges are refused unless a self-hosted policy names a host, and every 3xx response counts as a failure.
5. **Opaque references.** Above `public`, payloads carry a per-subscription id, the HMAC of the `ObjectId` under the subscription's key, never an `ObjectId` or file hash, so a third-party receiver cannot confirm a guessed value.
6. **People only.** Agents read events through `read.events` and MCP (Model Context Protocol) resource subscriptions to branch heads, Proposals and Evaluations (AGT).

### Where tenant bytes leave

A design is only as safe as its weakest exit, so ECO's exits share one set of checks. Tenant bytes leave through `release_data` Acts, through `api` responses to model contexts cleared for them, and through audited local writes (contract section 7.6); every exit compares both the confidentiality and the usage parts of the label.

ECO provides three exit surfaces:

- **Repository archive** (phase 1): a design repository's full history and the CAS objects needed to rebuild it; restoring it reproduces every Change's build hash.
- **Release bundle** (phase 1): a release's neutral Files, the bill of materials (BOM) as CSV and JSON, and the signed manifest.
- **Git mirror** (phase 2): a push of selected branches, with their commits, to another party's Git host.

The archive format and the CAS encoding are open, so a third party can write an independent reader (ECO-O-12). On import, spans keep their integrity only when the server that witnessed each write signed its span-integrity record and this organization trusts that server (KLN).

**Decision D-ECO-28:** Every ECO surface that sends tenant bytes to another party is an Act in AGT's `release_data` family: archive export, mirror pushes, release bundles, quote requests, connector messages, passports and publishing. At commit each runs one set of checks: labels, screening, a `ControlAuthorization` for controlled payloads, and audit. Recurring channels such as a Git mirror run as a `standing_release` that two people approve once, fixing recipients, channel, schema, confidentiality ceiling and an expiry of at most 12 months.
*Why:* exit paths with different controls leave the weakest open, and a standing release controls frequent flows without rubber-stamping each one.
*Rejected:* plain API methods for export; controls per exit path, which drift; one Approval per mirror push, which invites rubber-stamping.

### Enterprise connectors

Most organizations already run an ERP (enterprise resource planning), an MES (manufacturing execution system) and often an enterprise PLM, and Crucible must feed them without becoming a second integration project.

**Decision D-ECO-30:** ERP, MES and PLM systems connect through the connector worlds of `crucible:connect`, with field mappings as Packages of mapping data and a table of which system owns each field. A release or change-notice plan lists deliveries to the organization's own systems as effects under its one Approval (contract section 7.6), and failed deliveries retry until the plan expires. Other messages, such as a new-part request, are separate Acts or a `standing_release`, and inbound data arrive as signed External inputs. Mappings key by `Site`, a policy record naming a plant or contract manufacturer and its ERP mapping, so one engineering BOM (EBOM) revision maps to each plant's manufacturing BOM (MBOM), routings and work centres.
*Why:* mappings as data are reviewed like any package, an Approval per ERP message invites rubber-stamping, and products made in two plants need two mappings of one EBOM.
*Rejected:* a webhook consumer that only reads change notices; per-customer integration code; one Act per message; a single-site mapping.

Outbound records are `ItemMaster`, `BillOfMaterials`, `Routing`, `WorkOrder` and `ChangeNotice`, with routings and work orders mapped by MFG per `Site` from phase 2. Inbound External inputs carry cost, price, lead time and inventory for MFG's cost models. ERP messages follow OAGi's OAGIS business object documents [OAGi], and MES messages follow B2MML, the XML form of ISA-95 [B2MML].

| Field | Owner by default |
| --- | --- |
| Item number, revision label, lifecycle state | Crucible, or the external PLM under KLN's system-of-record policy |
| EBOM structure, reference designators, effectivity | Crucible (KLN) |
| MBOM, routings and work orders, per `Site` | Crucible (MFG) where it plans manufacturing, else the ERP |
| Cost, price, lead time, inventory | ERP, inbound |
| Stock disposition on change | Crucible decides; the ERP executes |

Under KLN's `External(connector)` system-of-record policy, numbers come through the PLM connector, and the release Act publishes into the external item revision. An external approval is a pinned record in the release, never an Approval: where the external system is the only approver, the release Act's Approval covers only the publication, and the release record says "approved externally" (KLN). Reference connectors for two ERP and three PLM systems arrive in phase 2.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| SDKs and C ABI | Generated from one catalog; `crucible-sdk` on every index | AGT's error object in every language | ECO-O-11 | 0 (Rust), 1 (Python), 2 |
| ECO's API methods and CLI | Methods in Reference; aliases, exit codes, offline mode | Typed errors; exit codes 1 to 5 | ECO-O-11 | 1, 2 (registry search and bundles) |
| Events and webhooks | CloudEvents; Standard Webhooks; PLT's egress proxy with ECO's address rules; opaque references above `public` | Retries, then dead-letter queue; refused addresses | ECO-O-14 | 1 |
| Repository archive and open encodings | Full history; independent readers | `archive/incomplete` | ECO-O-12 | 1 |
| Outbound Acts | `release_data` checks for every exit to another party | `label/write_down`; screening failure | ECO-O-28 | 1, 2 (mirror, standing releases), 3 (watermark) |
| ERP and MES connectors | Records out as release effects, mapped per `Site`; External inputs in | `MappingConflict { field, owner }` | ECO-O-27 | 2 (one site), 3 (several sites) |
| PLM subordinate mode | External numbering; external approvals as pinned records | `DigestMismatch { expected, found }` | ECO-O-27 | 2 |

## Package registry

Every package, from std and translators to solvers, panels and catalog parts, arrives through one registry, so its namespaces, signatures and holds decide whether a stranger can slip code into a design. Phase 1 ships a signed first-party index as TUF targets, and the public registry opens in phase 2 (contract section 13.2).

### Names and namespaces

**Decision D-ECO-13:** Every package lives in a namespace that a verified publisher owns, named `namespace::name` as Ingot's `use` writes it: domain claims own bare names, code-host claims take a prefix (`gh_<org>`, `gl_<org>`), and individuals get `u_<handle>`.
*Why:* code-host names are first-come, so a stranger could take the name acme.com needs, and Maven Central reuses DNS likewise [Maven Central namespaces].
*Rejected:* a flat namespace, open to squatting; optional scopes; unprefixed code-host claims.

| Rule | Detail |
| --- | --- |
| Syntax and spellings | Segments match `[a-z][a-z0-9]*(_[a-z][a-z0-9]*)*`; Ingot `parts::ti::tps62133`, WIT `parts:ti-tps62133`, URL `parts/ti/tps62133`; a WIT collision is refused |
| Reserved | `std`, `crucible`, `core`, `parts`, `standards`, `examples`, `wasi`, `test`, and the prefixes `u_`, `gh_` and `gl_` outside their claims |
| Look-alikes | Names within edit distance 1 of a popular one, or equal after mapping look-alikes, are held for review |
| New versions | A new version resolves for other organizations after a 72 h hold |
| Hold exception | A version skips the hold only when a party other than the package's publishers (the registry security team, the upstream database of OSV, the Open Source Vulnerabilities format, or a CVE numbering authority) published the advisory it fixes, it comes through the namespace's trusted publisher with an unchanged signer, and its diff from the previous version touches only the advisory's affected files or the registry security team reviewed it |
| Re-verification | Domain claims are re-verified yearly; a failed re-verification freezes the namespace, so existing versions resolve and nothing new publishes, and only the previous owner key, or the dispute policy with proof of continuity, unfreezes it; a new domain holder never inherits it |
| Transfer | By consent or the dispute policy, logged |

The hold exists for hijacked maintainer accounts, and the exception exists for urgent security fixes. Without its conditions, a hijacked account could file its own advisory and publish a malicious "fix" with it. PLT applies the same exception to Crucible's own dependencies.

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
world   = "crucible:connect/partner-connector@0.1.0"
context = "connector"
http    = ["api.acme.example"]           # the only reachable host
secrets = ["acme_api_token"]
```

The lockfile pins each package's version, registry, grants, source and binary hashes and signer identity, plus Assets and External inputs. A changed registry fails resolution, and the PubGrub algorithm's derivation tree becomes a typed explanation [PubGrub]. Crucible links the `pubgrub` crate under MPL-2.0's duties or reimplements the algorithm (contract 7.7).

At publish the registry refuses incompatible interface changes in minors and patches, as cargo-semver-checks does [cargo-semver-checks]. It records changed outputs and `EntityId`s on test designs, which depend only on source text through `CallSite`.

**Decision D-ECO-14:** A release may change outputs or entity names, but the registry publishes every such change and `crucible update` shows it first: an output-changing patch is labelled, a renaming release is at least a labelled minor, and policy can block both.
*Why:* a fix that moves geometry is a design change, and a renamed entity breaks anchors and PMI downstream.
*Rejected:* trusting authors' version numbers alone; forbidding output changes outside majors, which delays fixes.

### Publishing and signing

**Decision D-ECO-15:** Publishing never uses long-lived tokens: CI publishes through trusted publishing with a short-lived OpenID Connect (OIDC) credential, or a person publishes through a publish Act approved with an approval credential.
*Why:* crates.io and npm adopted trusted publishing in July 2025 [crates.io update 2025-07]. After the Shai-Hulud worm spread through maintainer accounts in September 2025, GitHub narrowed npm publishing to these paths [npm security plan].
*Rejected:* long-lived tokens, the main theft target; publishing without a phishing-resistant credential.

The pipeline runs in order, and a failure at any step returns a typed error with nothing published:

1. Verify the signer against the namespace policy, and the version's novelty.
2. Rebuild where the toolchain allows: first-party packages on the hermetic builder, third-party packages in single-use microVMs.
3. Determinize evaluation Wasm components in a code-free microVM on two hosts (D-ECO-8).
4. Run scanners, the publisher's export attestation check and the restricted-jurisdiction rule (D-ECO-29).
5. Run domain acceptance checks contributed as data, such as COV's validity-envelope checks.
6. Measure interface, output and entity-name changes (D-ECO-14).
7. Run test vectors on every engine (ECO-O-6).
8. Sign the index entry, with both determinizer receipts, and append it to the log.

For a third-party package, steps 2, 5, 6 and 7 run on untrusted-evaluation workers, and their results never enter the global public cache domain. Registry builders and the hermetic builder never run third-party code (contract section 7.8).

[[DIAGRAM diagrams/11-interop-publish-pipeline.jsx: publish pipeline · eight steps, one failure exit, verifying clients]]

Follow the arrows through steps 1 to 8: a failed step exits to the typed error, and clients verify what step 8 signs.

| Layer | Mechanism | Proves |
| --- | --- | --- |
| Author signature | Sigstore keyless signing, logged in Rekor [Sigstore] | Who published these bytes |
| Namespace policy | Trusted publishers signed by the owner's offline key | Who may publish here |
| Namespace delegation | Offline-signed `claimed` role; online-signed `recently-claimed` role for new namespaces | That an online key cannot re-delegate a claimed namespace |
| Build provenance | SLSA (Supply-chain Levels for Software Artifacts) provenance, as PyPI's attestations carry [SLSA] | Which source and builder made the bytes |
| Repository metadata | TUF, against rollback, freeze, mix-and-match and malicious mirrors [TUF spec] | Freshness and consistency |
| Transparency | An append-only log that clients verify and organizations may monitor | No split views |

**Decision D-ECO-16:** Every package version carries a Sigstore signature and SLSA provenance, and its signer must match the namespace's trusted-publisher policy, which the owner signs offline. Delegations follow PEP 480, still a Draft [PEP 480]. An offline `claimed` role holds claimed namespaces and is signed by its own threshold keys, held by the steward's security staff, with a 90-day expiry and monthly re-signing; root keyholders sign only root, which delegates to `claimed`. An online `recently-claimed` role holds new namespaces, and clients warn on first resolution from one. Owner-key recovery needs domain re-verification plus a `claimed` re-signing, and first-party packages are built at SLSA Build level 3 [SLSA build track] and reproduced bit for bit.
*Why:* with online keys alone, TUF cannot protect projects from a compromised registry, which could re-delegate any namespace [PEP 458]. A frequent threshold ceremony among outside root keyholders would expire the metadata the first week one is missed.
*Rejected:* the registry's own record of publishers; online-signed delegations; root keyholders re-signing `claimed` weekly; signatures without provenance; GPG keys.

From phase 2, TUF metadata, checkpoints and provenance are dual-signed, classical plus ML-DSA-87 [FIPS 204], and LMS serves only PLT's software-release signing (contract section 7.8). Air-gapped registries run their own Fulcio and Rekor, or sign with organization keys through `cosign sign --key` [cosign key signing].

### Scanning, advisories and removal

Every publish scans capabilities, signer changes, imports, network targets, secrets, advisories and malware. A malware finding quarantines the version for review within 24 h (target), no code runs at install, and Crucible's own crates carry cargo-vet audits (PLT).

Advisories use OSV 1.9.1, and ECO registers a `Crucible` ecosystem by pull request in phase 1, the route the schema documents [OSV]. A **correctness advisory** names an operation, translator or package version whose outputs were wrong, as an OSV record with `database_specific.kind = "correctness"`. Lockfiles let `repo` list every released design that used it.

| Act or method | Effect | Who |
| --- | --- | --- |
| Yank | New resolution skips the version; pinned bytes stay downloadable, as in Cargo [cargo yank] | Publisher, as an Act |
| Deprecate | A notice and an optional successor | Publisher, as a `yank_package` Act in its deprecation mode |
| Quarantine | Download stops; hosts refuse to instantiate; pinned designs fail with `PackageQuarantined` | Operator, with a statement of reasons (D-ECO-35) |
| Legal removal | After a court order or valid notice, and counter-notice where the law provides; a tombstone keeps the hash | Operator, with a statement of reasons |

**Decision D-ECO-17:** Publishers never delete published versions; yanking is their only tool, and leaked credentials go to revocation or an advisory.
*Why:* a released product must rebuild from the same pinned bytes for decades.
*Rejected:* a short unpublish window, as npm allows for 72 hours [npm unpublish], which breaks any release pinned inside it; unrestricted deletion.

### Mirrors, licences and the parts catalog

Mirrors are untrusted transport, since clients verify signatures, TUF metadata and log inclusion. Private registries run the same server and deny namespaces off the organization's allowlist, closing dependency confusion. Air-gapped sites import signed bundles, and components are also served in the OCI layout `wkg` reads [wasm-pkg-tools].

Every package declares SPDX expressions for code and data, checked per file in the style of REUSE 3.3 [REUSE 3.3] against organization policy. Each release manifest lists every package, translator and dataset used, so a release ships its software bill of materials.

A `CatalogSelection` is a pure function over pinned definitions, plus pinned offers when it ranks by price (ELX, ING). A `parts::<manufacturer>` namespace belongs to the manufacturer once it verifies, and the operator curates it until then.

**Decision D-ECO-18:** A catalog part's definition is a Package under `parts::<manufacturer>::…`; its offers, lifecycle states and product change notices are signed feeds that a connector turns into dated External inputs. Operator-curated `parts::` Packages hold only facts with datasheet citations and geometry Crucible's generators make from them. Manufacturer CAD files enter only where their terms allow redistribution, recorded in `geometry_licence`, and the registry refuses a missing or non-redistributable data licence. Lifecycle and change-notice updates land on a monitoring branch as `part.lifecycle_changed` and `part.change_notice` events, never on released source, and feed KLN's obsolescence check.
*Why:* definitions must be pinned like code, while offers and lifecycle states are volatile. Manufacturers often allow design use without redistribution, and an end-of-life notice must reach every released product that uses the part.
*Rejected:* hourly price versions in the registry; definitions outside it; republishing manufacturer models under Crucible's licence; applying lifecycle changes to released source.

Fastener geometry defaults to manufacturers' `parts::` packages published under their own terms, the model supplier catalogues already use, so a design never waits on a standards licence for a screw. Migrated KiCad library items stay in private Packages, or go public under CC-BY-SA-4.0 with attribution, since KiCad requires redistributed library collections to keep its licence [KiCad library licence].

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Signed first-party index | TUF targets from the hermetic builder | Client refuses unverifiable entries | ECO-O-9 | 1 |
| Public registry and trusted publishing | OIDC publishing or an approved publish Act; the pipeline | Typed error naming the step | ECO-O-9, ECO-O-19 | 2 |
| Namespaces | Prefixes, holds and their exception, re-verification freeze, `claimed` roles | `NamespaceTaken`, `HeldForReview`, `NamespaceFrozen` | ECO-O-9, ECO-O-19 | 2 |
| Resolution and lockfile | PubGrub; signer and registry pinned | `Unsatisfiable`; `SignerChanged` awaits approval | ECO-O-9 | 0 |
| Compatibility labels | Interface, output and entity-name diffs | Refusal naming the item | ECO-O-10 | 1 |
| Signing, policies and transparency | Sigstore, SLSA, offline policies, TUF, log | Client refuses | ECO-O-9 | 1 (first-party), 2 |
| Post-quantum dual signatures | ML-DSA-87 beside the classical algorithm | Single-signed records fail verification | ECO-O-9 | 2 |
| Scanning, advisories, removal | Scans, OSV advisories, yanks, removal with reasons | Quarantine; `PackageRemoved` | ECO-O-19, ECO-O-29 | 2 |
| Private registries and bundles | Deny-by-default namespace map; offline bundles | `NamespaceNotAllowed` | ECO-O-9 | 2 |
| Licence metadata | SPDX, per-file coverage, policy | Invalid expressions refused | ECO-O-31 | 1 |
| Catalog-part definitions | Facts and generated geometry; offers as External inputs | Licence refusal | ECO-O-16, ECO-O-31 | 2 |
| Part lifecycle feeds | Lifecycle states and change notices as dated External inputs on a monitoring branch | `FeedStale { source, since }` | ECO-O-27 | 3 |

## Marketplace

Publishers who build specialist solvers, catalogs or integrations need a way to be paid, and buyers need designs that never become hostage to billing; the marketplace is the registry's commercial layer, with no second distribution system. Listings open with the public registry in phase 2, and paid packages in phase 3.

| Publisher level | Requirement | Grants |
| --- | --- | --- |
| Account | Verified email and phishing-resistant 2FA | `u_<handle>` |
| Organization | A domain verified by DNS TXT, or a code-host organization by OIDC (prefixed) | A namespace for it |
| Verified publisher | Know-your-business checks with screening against the restricted-jurisdiction dataset, trader data, a security contact, the publisher agreement | Paid packages; manufacturer-verified catalog parts |
| Certified integration | A passed integration suite | Listing in ordering and quoting flows |

Badges link to the dated record of the checks that ran and never claim quality.

**Decision D-ECO-32:** Verification changes badges, never integrity: all third-party package text reaches readers as `ExternalText`, verified publisher or not, and only first-party documentation from the hermetic builder is trusted.
*Why:* verification establishes who published, not that the text is safe to obey, and a compromised account would otherwise instruct agents.
*Rejected:* trusting verified publishers' text.

Role skills are instructions by design, so AGT serves a third-party role skill to any host only after `policy:admin` approves its version and digest for the organization.

**Decision D-ECO-19:** Paid packages are ordinary registry packages whose download needs a signed, offline-verifiable entitlement, checked before instantiation and never during evaluation, and a design that pins a paid version rebuilds with it forever. The steward company is merchant of record: it buys from publishers, invoices buyers and collects VAT and sales tax per jurisdiction.
*Why:* evaluation stays offline and designs never become hostage to billing, and EU VAT law treats a platform that authorises the charge or sets the terms as the supplier [EU VAT 1042/2013].
*Rejected:* licence checks inside components; a separate commercial store; naming publishers as suppliers, which the VAT rule overrides.

| Rule | Detail |
| --- | --- |
| Expiry | Blocks new versions and installs only; every paid version stays downloadable for any organization that ever held an entitlement |
| Results | Ordinary CAS objects; a collaborator without an entitlement gets `EntitlementRequired`, never cached, only when an input changes |
| Source | Compiled components with public worlds and test vectors; escrowed source scanned privately |
| Escrow | Source and build recipe with an independent agent; licensees may rebuild if the publisher stops for 12 months; counsel confirms the agreement per jurisdiction first |
| Export and sanctions | A declared `export_classification` (ECCN, EAR99 or not subject, with the basis); screened purchases; the restricted-jurisdiction rule of D-ECO-29 |
| Pricing and terms | Per seat, organization or usage, metered outside evaluation; the steward's terms govern refunds and disputes |

Suppliers publish one `offer` record (price breaks, stock, lead time, validity) through a connector. Manufacturing partners implement `crucible:connect/partner`: quote requests run inside `request_quote` Acts and orders inside `order` Acts. Quotes return as External inputs, and a partner earns "Certified" for 12 months on a published suite.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Verified publishers | Business checks, screening, trader data, dated badges | Verification refused, naming the failed check | ECO-O-29 | 2 |
| Third-party text as `ExternalText` | Every publisher's READMEs, docs, templates and definitions | None: text is only ever returned by handle, so there is no path to fail | ECO-O-18 | 2 |
| Paid packages, escrow and scanning | Offline entitlements; merchant of record; escrow; private scans | `EntitlementRequired`, never cached; listing refused on a finding | ECO-O-20, ECO-O-29 | 3 |
| Supplier offers | One `offer` record as dated External inputs | Stale offers flagged in Proposals | ECO-O-16 | 2 |
| Manufacturing partners | Quotes and orders inside Acts; certification suite | `partner-error` mapped to typed errors | ECO-O-28 | 2, 3 (certification) |

## Open-source governance and compliance

Product data lives for decades, so the code that reads it must stay open, rebuildable and lawful to use long after any company's plans change. This section fixes the licence, how contributions enter, who stewards the project, how releases are supported and how the project meets security, sanctions and liability law.

### Licence and contributions

**Decision D-ECO-20:** Crucible's code, std, SDKs, WIT packages and translators included, is licensed Apache-2.0 WITH LLVM-exception; documentation is CC-BY-4.0 and examples are MIT-0. The CAS encoding and archive format carry the steward's Open Web Foundation Final Specification Agreement 1.0, a royalty-free patent promise [OWFa 1.0].
*Why:* the toolchain embeds its code in artifacts users ship, which the LLVM exception covers [LLVM exception]. Apache-2.0's patent licence ends for anyone who sues [Apache-2.0], and the licence matches Crucible's Rust and Wasm dependencies.
*Rejected:* MPL-2.0, whose per-file duties land on every embedder [MPL FAQ]; MIT OR Apache-2.0, without a patent grant; an unnamed patent commitment.

Contract section 7.7 fixes which dependency licences may be linked, bundled or run only as external tools, and each linked MPL-2.0 file brings a notice and a source offer to every distribution [MPL-2.0]. ECO keeps the allowlist that PLT's cargo-deny and ECO-O-31 enforce, and any other licence needs an RFC.

**Decision D-ECO-36:** std computes standard values from the formulas the standards define, citing clauses, and ships no transcribed tables. A designation that carries its own pitch, such as `M5x0.8` or `1/4-20 UNC-2B`, and a clearance hole given by diameter or fit resolve with no table, so a design compiles with no licensed package installed. Table-only values (coarse-pitch series, clearance-hole series, fastener dimensions) ship in separate `crucible::standards::` Packages with a `DataLicence`, licensed from the standards body or supplied by the organization. Counsel's phase 0 opinion decides which series std may ship (contract section 13.1).
*Why:* standards bodies hold copyright, and ISO allows its files only "in their original format without any modifications" [ISO 10303 portal]. Substantial extraction can also infringe the EU database right [Directive 96/9/EC], and a new user's first tapped hole must not fail on a missing table.
*Rejected:* tables in Apache-2.0 std, a right Crucible cannot grant; no standards content, which leaves `fit(10mm, H7)` unavailable; requiring a licensed series table for every thread, which breaks a first design.

MEC owns the designations, the formula packages and the clearance rules; ECO owns the licence rule for the table packages.

**Decision D-ECO-21:** External contributions come under the Developer Certificate of Origin 1.1, with no CLA. Agent-written commits carry `Assisted-by: <tool, model>` and a founder `Reviewed-by`, never `Signed-off-by`. The licence notice states that portions may not be protected by copyright, so the patent grant and the trademark policy carry the project's protection, and counsel's written opinion on authorship and the DCO is a phase 0 gate item (contract section 13.1). Every contribution's added code runs a similarity scan against copyleft and permissive corpora, with thresholds per file and per contributor per week. A copyleft match blocks the merge; a permissive match passes only when the file carries the source's notice and the licence is on contract 7.7's list.
*Why:* the DCO certifies origin, not review, since clause (a) speaks of a contribution "created in whole or in part by me" [DCO]. The US Copyright Office concludes that prompts alone do not make a user the author of a system's output [Copyright Office 2025]. Agents also reproduce permissive code, whose notices must ship.
*Rejected:* a CLA with assignment, which enables relicensing; provenance trailers alone; a human `Signed-off-by` on agent-written code, which certifies something the human did not do; scanning only against copyleft code.

`ChangeProvenance` is mirrored into the public history. Protected paths such as `oracles/` change only through the oracle role and the verifier (contract section 13.2).

### Stewardship and decisions

**Decision D-ECO-22:** The founding company stewards the project until a fixed trigger, then transfers repositories, trademarks and namespace authority to an existing foundation that already holds trademarks and runs infrastructure. The trigger is the earliest of three events: the phase 3 gate, a year with maintainers from three other organizations, and three years after the first stable release. From phase 0 the foundation holds an irrevocable, recorded option on the trademarks with their goodwill, and the company keeps quality control until the trigger. A key ceremony gives the TUF root keys to keyholders at least half of whom are outside the company.
*Why:* product data lives for decades, so the kernel must be safe from relicensing or capture. A US mark passes only with its goodwill [15 USC 1060], and one whose owner lets it lose significance is abandoned [15 USC 1127].
*Rejected:* trademark escrow, with an owner that controls nothing; a new foundation, with no staff; a foundation at launch (contract section 7.7); a charter sentence alone.

The company keeps hosted services, the marketplace, licensed translators, support and certification. Before the transfer the founder decides governance; after it, a steering committee does, with at most one third of seats from one employer.

Significant changes go through public RFCs modelled on Rust's: new operation families, editions, WIT packages, capabilities, registry and licence policy. A shepherd is assigned within 14 days (target), and a ten-day final comment period precedes a written decision. Agents may draft RFCs; only humans approve them.

### Releases, support and liability

PLT owns the release train, with a yearly LTS supported for 24 months [Wasmtime releases], and the regulated cloud mode for defence customers [DFARS 7012]. The registry keeps every version a supported line's designs pin.

ECO assembles the Computer Software Assurance package for medical customers under FDA's guidance [FDA CSA]: risk tiers, oracle results, impact notes and a quality agreement template.

**Decision D-ECO-34:** Until the transfer, the company is the CRA (EU Cyber Resilience Act) manufacturer of every distribution it publishes, open-source releases included, with conformity assessment done by 11 December 2027 [CRA]. Each stable line states a support period of at least five years, and security fixes reach it by backport or by a free upgrade that raises no OS or hardware minimum, as separate patch releases.
*Why:* the CRA's Recital 15 counts monetising through a platform as commercial activity, and Article 13(8) sets the five-year floor. Article 13(10) allows latest-only support through a free upgrade, and Annex I Part II(2) asks for separate security updates.
*Rejected:* manufacturer duties for commercial builds only; the 24-month LTS as the support period, below the floor.

**Decision D-ECO-42:** Before phase 1 general availability, as the phase 1 gate requires (contract 13.1), counsel assesses the steward's product-liability exposure under Directive (EU) 2024/2853 and US law for hosted and commercial distributions. The commercial terms, the product information shipped with each release (validity envelopes, the meaning of `Estimated` bounds and `Undecided` verdicts) and the C1 advisory process follow that assessment, and the program budget carries the insurance it recommends.
*Why:* engineers release safety-critical parts on `SignOff` verdicts. The EU's new directive covers "all types of software" and applies to products placed on the market from 9 December 2026, inside phase 1 [EC product liability].
*Rejected:* relying on the open-source licence's warranty disclaimer for commercial distributions; handling the CRA alone, which covers security but not liability for a non-conservative result.

**Decision D-ECO-23:** Ingot uses per-package editions, as Rust does: editions interoperate in one build and change only surface syntax, prelude and lints, `crucible migrate` applies the fixes, and an edition never changes a pinned operation's behaviour version.
*Why:* every edition compiles to one internal form [Rust editions], so a migration is checked by rebuilding.
*Rejected:* versioning the language in lockstep, which forces every package to migrate at once; no editions, which freezes early mistakes.

A migration must leave every golden product's and registry test design's output hashes unchanged (ECO-O-13). Editions are named by year, at most one every three years (target), and ING owns the rules within one.

### Security, sanctions and names

Reports go to `security@`, to `/.well-known/security.txt` with its required Contact and Expires fields [RFC 9116], or to the code host. Acknowledgment comes within 2 business days (target), the 90-day embargo shortens under exploitation, and a bounty starts in phase 2. Identifiers are OSV and code-host ids until the public registry opens, when the steward applies for CVE numbering-authority scope over its products.

An actively exploited vulnerability gets an early warning within 24 hours and a notification within 72 hours, whatever the embargo; these CRA Article 14 duties apply from 11 September 2026. After the transfer the foundation takes Article 24's steward duties.

Correctness defects that could make a product unsafe get the same urgency:

| Severity | Meaning | Response |
| --- | --- | --- |
| C1 | A `SignOff` result is non-conservative, or an export moves manufactured geometry beyond tolerance | Advisory within 72 hours of confirmation (target); affected-release owners notified through `repo` |
| C2 | An `Interactive` result or non-critical export is wrong beyond its bound | Advisory with the next stable release |
| C3 | Metadata or presentation only | Changelog entry |

**Decision D-ECO-29:** The steward classifies each distributable under the US Export Administration Regulations (EAR) and the EU dual-use regime and publishes the statements, and public source with non-standard cryptography is notified to BIS and the NSA [15 CFR 742.15]. Every public package version carries the publisher's attestation that it contains no technical data controlled under the International Traffic in Arms Regulations (ITAR) or the EAR, or names the authorization for its publication. The registry refuses packages whose label has `controls`, and a DSA notice of controlled content quarantines the version pending review. Onboarding, purchases, support and update clients are refused for parties located or established in a jurisdiction of the pinned restricted-jurisdiction dataset. That dataset holds every country or region under a comprehensive EAR part 746 embargo or one of the US Treasury's (OFAC) comprehensive sanctions programs plus the EU and US sector restrictions on Russia and Belarus, and counsel signs each version.
*Why:* part 746 keeps comprehensive controls on Cuba, North Korea, the occupied regions of Ukraine, Iran and Syria beside Russia and Belarus [15 CFR 746]. The US requires a licence for EAR99 CAD, CAM, PLM and BIM software and updates to Russia [15 CFR 746.8], and the EU bars industrial design and manufacture software for entities established there [EU 833/2014]. Free packages are where an unaware engineer would post a controlled design.
*Rejected:* deferring export control; a Russia and Belarus rule alone, which drops the comprehensive embargoes; export classification for paid packages only.

Onboarding screens establishment and ownership, update servers geo-restrict the dataset's jurisdictions, and every dataset change is an explicit pinned update. Counsel decides once whether public open-source downloads need the authorisation route of Article 5n(9b) of the EU regulation.

**Decision D-ECO-35:** From its opening, the public registry runs notice and moderation as an online platform. Anyone may file an electronic notice of illegal content, export-controlled and sanctioned content included (Article 16 of the EU Digital Services Act, DSA). Every operator yank, quarantine or removal sends the publisher a logged statement of reasons (Article 17), which the publisher may appeal (Article 20). A yearly transparency report is published, paid listings need trader data (Article 30), and a designated agent under the US Digital Millennium Copyright Act (DMCA) and repeat-infringer policy apply [17 USC 512].
*Why:* the registry disseminates publishers' content to the public, and Articles 16 and 17 bind every hosting service [DSA].
*Rejected:* removal on court orders alone; relying on the small-enterprise exemptions of Articles 15(2), 19 and 29, which needs a second process later.

Every user-visible name is a phase 0 gate item (contract section 13.1): Crucible, Ingot and `.ingot`, Anvil, Kiln, Flux's replacement, and every crate, package and CLI name. Each is cleared in classes 9 and 42 or replaced before any operation version or WIT package freezes. "Crucible" gets full clearance in the US, EU, UK, China and Japan, since Atlassian still lists Crucible as its mark [Atlassian trademarks]. Atlassian's product sales ended in 2025 [Atlassian Crucible], and the brief also covers lapsed products such as Amazon Game Studios' 2020 game [Crucible game]. Flux is renamed, since Siemens sells Simcenter Flux [Simcenter Flux] and flux.ai is a PCB tool [Flux AI]. Kiln is at risk: Fog Creek's Kiln was commercial Mercurial hosting with a code-review tool [Kiln FogBugz], the same goods as KLN's `repo`.

The trademark policy allows "works with Crucible" without implying official status. "Crucible-compatible" needs the conformance suite, and modified distributions need another name.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Licence policy | Contract section 7.7's list; source offers; no standards tables in std; designations with pitch need no table | A violating distribution is not released | ECO-O-31 | 0 |
| Contribution checks | DCO for external contributors; `Assisted-by` and founder `Reviewed-by` on agent commits; similarity scan against copyleft and permissive corpora | Merge blocked, naming the rule | ECO-O-30 | 0 |
| Binding stewardship | Trigger with backstop; recorded trademark option; key ceremony; separate `claimed` keys | Root metadata below the keyholder threshold fails verification | ECO-O-9 | 0 |
| Regulated support artifacts | Pinned versions kept; CSA package per LTS | Line not promoted | ECO-O-22 | 2 |
| CRA manufacturer duties | Five-year support periods; separate security patches; 24 h and 72 h reports | A missed deadline is recorded as an incident | ECO-O-29 | 1 |
| Product-liability assessment | Counsel's assessment before phase 1 general availability; release information and terms follow it | `ReleaseBlocked { reason: LiabilityAssessmentMissing }` | ECO-O-29 | 1 |
| Export classification and restricted jurisdictions | Statements; publisher attestations; registry refusals; jurisdiction refusals from the pinned dataset | `ExportControlled`, `JurisdictionRestricted`, `AttestationMissing` | ECO-O-29 | 1 |
| Notices and moderation | Notices, statements of reasons, complaints, DMCA agent | A removal without reasons fails the drill | ECO-O-29 | 2 |
| Name clearance | Every user-visible name cleared or replaced and reserved before freezes | Freeze refused while uncleared | ECO-O-6 | 0 |

## Documentation and community

A platform anyone may extend needs documentation people trust and a community with rules, so this section sets the system that AGT's agent-facing references and UIX's scripted tutorials sit in.

**Decision D-ECO-24:** Documentation follows the four Diátaxis types (tutorials, how-to guides, reference and explanation) [Diátaxis], reference is generated, and every code sample is a tested example.
*Why:* each type serves one need, and generated reference cannot drift.
*Rejected:* a single manual, which mixes learning and lookup; a wiki, which is untested.

Tutorials follow each golden product from sketch to release. Every code block builds with its checks passing, every public item has an example and units, and pages ship offline with the desktop app. The registry generates reference docs for every package.

The community has a forum, chat and an issue tracker under the Contributor Covenant 3.0 [Contributor Covenant]. Certification is graded by oracles: practicals with hidden checks, and hidden test vectors for package developers.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Documentation site | Diátaxis; tested examples; offline copy | A failing example or uncovered item blocks the release | ECO-O-32 | 1 |
| Package reference docs | Generated per version at publish | Missing docs warn; std refuses | ECO-O-32 | 2 |
| Certification | Practicals from a rotating held-out pool | Fail with the failed checks listed | ECO-O-32 | 2 |

## Migration from incumbent tools

A team adopts Crucible only if it can bring its existing designs, programs and libraries, and keep working beside the tools it still runs. This section says what moves, how, and how far design intent can be recovered.

### What can move

| Source data | Moves as | Path | Phase |
| --- | --- | --- | --- |
| Part geometry, assembly structure, properties | `Body` with identity, `Assembly` of Instances, metadata | AP242, Parasolid or licensed readers | 1 (STEP), 2 (licensed) |
| Semantic PMI; mates | Geometric dimensioning and tolerancing (GD&T) on faces, presentation-only and flagged where the source has no semantics; mates where exposed, else fixed placements | AP242, or a licensed reader as its qualification record states | 2; 3 |
| Drawings; PDM history | DXF and DWG as editable drawing programs, PDF as Assets; released revisions without feature history | Files; PLM connectors (D-ECO-30) | 2; 4 |
| Live native CAD files | `Document` Items with the reference graph the licensed reader extracts (referenced files and configurations), so where-used and release completeness cover them; Crucible never edits them | Licensed readers; KLN's Items | 3 |
| NC programs | `Program` Items verified by MFG's `verify_nc`, never converted; macro calls need the machine's macro library (MFG) | Bulk import | 2 |
| Tool libraries, posts, setup sheets | Tool Assemblies through the tool-data readers; posts and sheets as Assets | Bulk import | 2 |
| ECAD designs and libraries | Schematics, boards, symbols, footprints and parameters; library parts become catalog parts (ELX) | Own EAGLE XML reader; KiCad for the rest (D-ECO-31) | 3 |
| Boards without schematics | Layout, netlist and BOM | IPC-2581 and ODB++ read | 3 |
| Analysis models | Nastran, Abaqus and LS-DYNA decks as runnable studies (D-ECO-40); Modelica source as Networks (D-ECO-41) | `io/` readers | 3; 4 |

**Decision D-ECO-31:** Proprietary ECAD designs migrate through KiCad 10's importers in a pinned container, then Crucible's own KiCad reader, and EAGLE XML gets its own reader.
*Why:* Autodesk ended EAGLE sales and support on 7 June 2026 [EAGLE]. KiCad 9 imports EAGLE, CADSTAR, EasyEDA, Altium, P-CAD and Fabmaster [KiCad 9 docs]. KiCad 10 adds Allegro, PADS and gEDA or Lepton PCB [KiCad 10], the Cadence and Siemens formats whose users most need a path. KiCad is GPL-3.0 or later [KiCad licences], so it runs only out of process.
*Rejected:* licensed ECAD translators, which mostly do not exist; own readers for every undocumented format.

**Decision D-ECO-25:** Crucible does not import parametric feature history from proprietary systems: it imports geometry, structure, semantic PMI and metadata, and offers design-intent reconstruction as a reviewed Proposal.
*Why:* replaying undocumented features without the original kernel gives different geometry, silently, while reconstruction can be checked.
*Rejected:* feature trees through licensed SDKs, fragile per version; macro-recording replay.

Configurations, design tables, equations and sketches stay behind; their results arrive as geometry. Teams that keep live SOLIDWORKS, Creo or NX files beside Crucible designs manage them as `Document` Items, and where the enterprise PLM stays the system of record, subordinate mode releases into it.

### Reconstruction and tooling

Reconstruction, run by an agent role and delivered as a Proposal, has four steps:

1. **Recognize** extrusions, holes with `HoleSpec`, fillets, chamfers, patterns, shells and drafts: rules for prismatic parts, learned segmentation for the rest. BRepNet's convolutions over oriented coedges inform the model [BRepNet], and shipped models train only on Crucible's procedural corpus and licensed data under AGT's training rule.
2. **Generate** Ingot features with std features and the imported PMI as constraints.
3. **Verify** against the import: Hausdorff distance under 1 µm (target), equal topology in normal form, every PMI item re-attached through a `Query`.
4. **Fall back** to imported geometry for regions that fail, joined by direct-edit operations and listed.

The phase 3 target: 9 of 11 NIST parts and 80% of a held-out prismatic set rebuild with all PMI.

| Source or tool | Approach | Phase |
| --- | --- | --- |
| OpenSCAD sources; spreadsheet design tables | Own translator for CSG, extrusions and modules, with OpenSCAD (GPL-2.0 [OpenSCAD COPYING]) only as an external oracle; tables become parameter files and variant sets | 2 |
| Zoo KCL [KCL docs]; CadQuery and build123d, Apache-2.0 on Open CASCADE [CadQuery] | KCL translated, pipelines to `\|>`; Python sources run in a pinned container whose operation trace becomes Ingot | 3 |
| The organization's own Onshape FeatureScript | Translator for std calls, units and sketches, tested on the licence-filtered ABC subset; unknown calls become `Untranslated` stubs | 4 |
| `crucible import scan` and bulk import | Inventory of formats, broken references and duplicates; resumable | 2 |
| Subordinate mode | The enterprise PLM stays the system of record while Crucible releases into it (D-ECO-30) | 2 |
| Parallel run, round-trip bridge, library migration | Re-import incumbent releases and report differences; standard parts to Packages | 3 |

Translators run in the tool context and must match the original's STEP export within tolerance. Migration never modifies source data, and every converted model keeps its source File by hash.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| MCAD migration | Geometry, structure, PMI, metadata, drawings | Per-file report; `ImportError` per dropped entity | ECO-O-1, ECO-O-17 | 1 to 4 per row |
| Native CAD reference graphs | Referenced files and configurations extracted at import for KLN's `Document` Items | `UnresolvedReference { file }`. Requires: KLN Foreign native CAD files | ECO-O-15 | 3 |
| Manufacturing-data migration | Programs, tool libraries, posts and setup sheets | No transfer until the program Item's subject is approved, else MFG's `PlanUnapproved`. Requires: MFG External NC verification | ECO-O-17 | 2 |
| ECAD migration | EAGLE reader; KiCad 10 as an external tool; legacy board read | `Untranslated { construct }` per file | ECO-O-25 | 3 |
| Reconstruction and source translators | Recognize, generate, verify, fall back | `ReconstructionIncomplete { regions }`; those regions stay imported | ECO-O-21 | 2 to 4 per row |
| Inventory, bulk import, subordinate mode | Scan, convert, coexist | Per-file report; resumable | ECO-O-17, ECO-O-27 | 2 |

## Reference

### Format catalog

Versions were checked in October 2026. "Owner" names the tab that defines the data's meaning; ECO owns the translator.

#### Mechanical CAD and product data

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| STEP AP242, Part 21 | ISO 10303-242:2025, edition 4 [ISO 242] | R/W | Identity | Build | 1: geometry, structure, properties, PMI write. 2: PMI read, persistent ids. 3: kinematics. 4: composites | ANV, MEC |
| AP242 edition 5 schema; domain model XML | Used in CAx-IF round 58J [CAx-IF 58J] | R/W | Semantics; structure | Build | 3 | MEC; KLN |
| STEP AP203, AP214 | Edition 2; edition 3 [CAx-IF GVP] | R; W | Structure | Build | 1 (R), 2 (W) | ANV |
| STEP AP209 | Extension of AP242 [ISO 10303 wiki] | R/W | Semantics: FE models, results as Fields | Build | 4 | FLX |
| STEP AP238 and ISO 14649 | ISO 10303-238:2022, as MFG states | R/W | Semantics: workingsteps | Build | 3; parts 13, 14 and 17 at 5 | MFG |
| STEP AP239; AP233 | At phase 5 | R/W; R | Structure | Build | 5 | KLN; ELX |
| IGES | 5.3 of 1996, the last [IGES wiki] | R; W | Geometry | Build | 1 (R), 2 (W) | ANV |
| JT | ISO 14306-1:2024 [ISO 14306] | R/W | Structure, B-rep, PMI | License [HOOPS Exchange], then own reader from the standard | 2 (License), 4 (Build) | ANV |
| Parasolid; ACIS | Vendor formats | R/W | Structure, exact geometry | License | 2 | ANV |
| CATIA V5, NX, Creo, SOLIDWORKS, Inventor | Per translator | R | Structure, PMI, reference graph | License | 2; 3 (reference graph) | ANV, MEC, KLN |
| Solid Edge; Rhino | Per translator | R (Rhino R/W) | Structure | License | 3 | ANV |
| PDF; SVG; PDF/A | PDF 2.0; SVG 1.1 Second Edition [SVG 1.1]; PDF/A-2u (ISO 19005-2:2011) for release drawings and PDF/A-4 (ISO 19005-4:2020) as MEC's option [PDF/A wiki] | W | Visual: drawing sheets | Build | 1 | MEC |
| DXF | R12 to R2018 [acadrust] | W of sheets and planar sections; R/W | 2D geometry, layers, blocks, flat patterns | Adopt (D-ECO-39) | 1 (W of sheets), 2 (R/W) | MEC, MFG |
| DWG | R13 to R2018 | R/W | 2D geometry, layers, blocks | Adopt; License for other versions | 2 | MEC, MFG |

#### Mesh, additive manufacturing, scans and buildings

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
| IFC | IFC 4.3, ISO 16739-1:2024 [ISO 16739] | R/W | Semantics of members, plates, openings | Build on the STEP layers | 5 | MEC |

A producer must mark the Beam Lattice extension required, and a consumer without it must refuse the file [3MF beam lattice]. So GP2's writer also emits a Core mesh 3MF at a declared chordal error and triangle budget, for the bureau's file-acceptance test (contract section 13.2).

#### Electronics

ELX owns the board model, MFG the factory hand-off, and ECO the `io/` readers and writers.

| Format | Version | R/W | Level | Strategy | Phase |
| --- | --- | --- | --- | --- | --- |
| IDF; STEP boards | IDF as KiCad exports it [KiCad 9 PCB editor]; AP242 or AP214 | R | Outline, holes, keep-outs, part heights, designators | Build | 2 |
| IDX | V6.0, December 2025 [prostep IDX] | R/W, incremental | Identity | Build | 2 (baseline import), 4 |
| IPC-2581 | Revision C [IPC-2581C] | R/W | Semantics: stackup, netlist, BOM | Build | 3 |
| ODB++ | ODB++Design 8.1 update 3 [ODB++ 8.1] | R/W | As IPC-2581 | Build; KiCad's writer [KiCad 9.0] as oracle, never linked | 3 |
| Gerber X2 and X3, job file, XNC | Gerber 2026.05 of 19 May 2026; job 2020.08; XNC 2021.11 [Ucamco Gerber] | W; R to verify | Copper, mask, attributes | Build | 3 |
| KiCad files | S-expression formats [KiCad formats] | R; W of libraries and netlists | Semantics | Build | 3 |
| EDIF; IPC-D-356; Specctra DSN and SES; placements | EDIF 2 0 0, ANSI/EIA-548-1988 [EDIF wiki]; others per ELX | W (SES R) | Connectivity, routing, placement | Build | 3 |
| Touchstone, IBIS; VEC | 2.1 and 8.0; VEC 2.2.0, per ELX | R/W | Catalog-part models; harnesses | Build | 3; 4 |
| KBL | At phase 5, per ELX | R | Harnesses | Build | 5 |
| SPICE netlists and models; Verilog-A | The ngspice, PSpice and LTspice dialects ELX reads | R; W of netlists | Circuits and device models | Build | 3 |
| Allegro, PADS, Altium, CADSTAR, EasyEDA, P-CAD, Fabmaster, gEDA | KiCad 10's importers [KiCad 10] | R, migration only | Schematic, board, libraries | KiCad as an external tool (D-ECO-31) | 3 |

#### Simulation and analysis

FLX owns the FMI and SSP runtime, and ECO owns FMU packaging, FMI-LS-WASM included; phases follow contract section 13.4.

| Format | Version | R/W | Level | Strategy | Phase | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| FMI | 3.0.2 [FMI 3.0.2 news], 3.0.3 announced [Modelica newsletter 2026-02]; 2.0.5 for import | R/W | Semantics | Build | 3 (R, contract 13.4's FMU import row), 4 (W) | FLX |
| FMI layered standards | LS-XCP 1.0.0, LS-BUS 1.3.0-beta.1, LS-STRUCT 1.0.0-rc.1, LS-REF 1.0.0-beta.1, LS-DAE 1.0.0-alpha.1 [FMI site] | R; LS-BUS W | Kept and reported when unsupported | Build | 4 | FLX, ELX |
| FMI-LS-WASM | Non-normative prototype mapping the FMI C API to WIT [fmi-ls-wasm] | R/W, gated | Portable FMUs | Build; ECO joins the group | 3 (R), 4 (W) | FLX |
| SSP | 2.0.1 [SSP site] | R/W | Structure | Build | 4 | FLX |
| Modelica source | A declared subset of the language; MSL 4.1.0 examples as the corpus [MSL] | R | Networks | Build on Rumoca or a clean-room parser (D-ECO-41) | 4 | ELX, FLX |
| CGNS; Exodus II | CGNS 4.5.2 [CGNS releases]; Exodus from BSD-licensed SEACAS [SEACAS] | R/W | Meshes and solutions as Fields | Wrap (D-ECO-4) | 4 | FLX |
| VTK, VTKHDF | VTKHDF 2.8 [VTKHDF] | W; R | Fields on meshes | Build | 2 | FLX |
| Nastran bulk data and OP2 | Dialects from FLX's test models; pyNastran as oracle [pyNastran] | R/W; OP2 R | FE models as runnable studies; OP2 results as Fields | Build | 3 | FLX |
| Nastran DMIG and OP4 | Craig–Bampton reductions | W | Reduced matrices | Build | 3 | FLX |
| Abaqus input | Keywords from FLX's test models; meshio as oracle [meshio] | R/W | FE models as runnable studies | Build | 3 | FLX |
| LS-DYNA keyword | Meshes, parts, materials and contacts for GP5's drop model | R | FE models | Build | 3 | FLX |
| OpenFOAM case | OpenCFD v2606 [OpenFOAM v2606]; Foundation OpenFOAM 14 [OpenFOAM 14] | R/W | Mesh, conditions, fields | Build; the solver only as an External Op | 4 | FLX, COV |

#### Manufacturing, metrology, systems and materials

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
| GDSII; OASIS | At phase 5 | R/W | Mask and package layers | 5 | COV, MEC |

All rows here are Build. G-code has no `io/` translator: MFG's posts write it through the `post-processor` world, and `verify_nc` reads it.

### Machine-definition sources

| Source | What it gives | Licence check | Phase |
| --- | --- | --- | --- |
| Machine builder's STEP model | Structure geometry for the kinematic chain | `geometry_licence` recorded from the builder's terms; refused if missing | 2 |
| Builder's specification sheet | Travels, rapids, accelerations, spindle curves | Entered as a cited External input; no redistribution | 2 |
| MTConnect device model | Axes and components of a connected machine [MTConnect 2.5.0] | Open standard | 3 |
| Controller kinematic parameters | Pivot lengths and offsets read through a controller connector | The organization's own machine data | 3 |
| CAM or verification vendor machine definitions | A complete machine model | Only through a vendor export the organization licenses, with the licence id recorded | 3 |

### WIT package index

Each owner specifies its package with an oracle that the published WIT matches.

| WIT package | Interfaces | Owner |
| --- | --- | --- |
| `crucible:units` | `si` | ECO, with ING |
| `crucible:ops` | `anvil`, `flux`: async, generated from the operations catalogs, with a batched form | ANV, FLX; ECO generates the bindings |
| `crucible:geom` | `types`, `build` | ANV |
| `crucible:field` | `types`, `build` | FLX |
| `crucible:product` | `types`, `build`, `read` | MEC, KLN |
| `crucible:host` | `diagnostics`, `progress` (write-only), `cas` (handle reads), `parallel`, `chunk-worker` | KLN; PLT specifies and implements `parallel` and `chunk-worker` |
| `crucible:io` | `types`, `read`, `write`; worlds `importer`, `exporter` | ECO |
| `crucible:physics`; `crucible:material` | `solve`; `model`; worlds `solver`, `constitutive` | COV, FLX |
| `crucible:mfg` | Worlds `toolpath-strategy`, `post-processor`, nesting, packing, slicer and recognizer | MFG |
| `crucible:ui` | `types` (arena trees), `view`, `canvas-host`, `canvas`; worlds `panel`, `canvas2d` | UIX |
| `crucible:api` | One interface per method group | AGT |
| `crucible:tool` | `process`, `external`; world `driver` | ECO, with PLT |
| `crucible:connect` | `types`, `secrets`, `partner`, `erp`, `mes`, `plm`, `quality`; worlds `partner-connector`, `erp-connector`, `mes-connector`, `plm-connector`, `quality-connector` | ECO, with MFG and KLN |

### ECO's WIT packages

| Package | Interfaces and main items | Failures | Phase |
| --- | --- | --- | --- |
| `crucible:units` | `si`: one `f64` alias per SI dimension, such as `length` | None: the Ingot wrapper checks dimensions | 0 |
| `crucible:io` | `types` (`source`, `sink`, options, receiver profile, `disposition`, `entry`); `read` (`probe`, `parse`); `write` (`emit` from a read-only `model-view`) | `import-error`, `export-error` | 1 |
| `crucible:tool` | `process` (spawn in PLT's sandbox without egress); `external` (requests to a licensed translator host) | `process-error`, `egress-denied`, `capability-denied` | 2 |
| `crucible:connect` | `types` (offers, lifecycle states, change notices, quotes, orders, sites); `secrets` (named, host-bound); `partner` (`request-quote`, `place-order`, `get-status`); `erp`, `mes`, `plm` (mapped records); `quality` (KLN's quality records) | `partner-error`, `mapping-conflict` | 2; 3 (`quality`) |

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

The `exporter` world mirrors it, writing from a read-only `model-view` into a `sink` that becomes a CAS blob, with the receiver profile among its options.

### API methods and CLI

| Method | Contract | Failure |
| --- | --- | --- |
| `read.packages`, `read.package` | Search by name, world, licence or badge; one package's manifest, signer, advisories and labels | `package/not_found` with nearest names |
| `compare.resolve` | Manifest plus lockfile → new lockfile and diff, not applied | `package/unsatisfiable` with the PubGrub explanation |
| `edit.grant_capability`, `edit.revoke_capability` | A scoped grant or revocation recorded in `ingot.lock` | `policy/denied` naming the rule |
| `read.events`, `read.subscribe`, `read.unsubscribe` | Events by cursor; webhook subscriptions, by people with `maintainer` or `admin` | `events/cursor_expired`; `events/url_refused` |
| `edit.import_archive` | Repository archive File → design repository, with KLN's integrity rule for imported spans | `archive/incomplete` listing missing objects |
| `read.registry_bundle` | Lockfile → signed offline bundle of its pinned packages | `package/unavailable` |

| CLI exit code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Check failures |
| 2 | Usage |
| 3 | Build error |
| 4 | Authorization |
| 5 | Infrastructure |

## State of the art

Figures are targets.

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| STEP AP242 translation | Schema-generated Part 21 plus CAx-IF practices [CAx-IF GVP] | Commercial translators in CAx-IF rounds; Open CASCADE 8.0.1 [OCCT releases] | Three-layer Rust translator (D-ECO-3) in every round (D-ECO-5) | Round results; volume and area within 0.05%; zero SFA errors; PMI statistics equal on every NIST case |
| STEP read throughput | Streaming Part 21, lazy resolution | Open CASCADE | Streaming, parallel translation, deterministic merge | A 1 GB file at least 2× Open CASCADE on the reference laptop; browser within 3× of native |
| Proprietary CAD import | Vendor SDK access | CAD Exchanger, HOOPS Exchange, Datakit [CAD Exchanger formats] | Licensed, out of process, without egress, signed and pinned (D-ECO-2) | Qualification on NIST and held-out native models |
| Export to receivers | Local tolerances per entity, as Parasolid's tolerant modelling [Jackson 1995] | Each receiver's own healing on import | Receiver profiles applied before export (D-ECO-38) | Zero entities below `min_feature` and every tolerant edge reported on the held-out corpus |
| Validation and repair | Validation properties as receiver oracles | Open CASCADE Shape Healing [OCCT shape healing] | `anvil::heal` with bounds per entity | Healed entities bounded; re-export within production thresholds |
| DXF and DWG | ODA's published DWG specification; open readers | AutoCAD; acadrust [acadrust] | acadrust linked under MPL-2.0 after audit, or an own codec (D-ECO-39) | Round trip of the held-out DWG corpus, entity counts equal to LibreDWG's reading |
| Solver decks | Card-level mapping to idealizations | Ansys Mechanical's Nastran export [Ansys Nastran export] | Typed mapping with `UnmappedCard` (D-ECO-40) | NAFEMS decks within 1% of reference values (FLX); every card read equal to pyNastran's |
| Modelica import | Index reduction and tearing on a flattened model | Dymola [Dymola] | Rumoca or a clean-room front end into Networks (D-ECO-41) | MSL example results within their tolerances; coverage share reported |
| Sandboxed extensions | Component Model async in the callback ABI [CM concurrency] | Wasmtime; jco [jco] | Async `crucible:ops` with ordered completions (D-ECO-9); one browser runtime (D-ECO-10) | Every first-party world on Wasmtime, JavaScriptCore, V8 and SpiderMonkey; ≤ 1.6× native Rust in Wasmtime, ≤ 2.5× in browsers |
| Deterministic execution | Injected metering [finite-wasm]; Wasm 3.0 deterministic profile [Wasm 3.0] | Wasmtime fuel, native only [Wasmtime determinism] | PLT's determinizer at publish on two code-free hosts (D-ECO-8) | Identical outputs and traps on 10⁴ vectors per component |
| Supply-chain integrity | Sigstore; SLSA v1.2; PEP 740; TUF with offline delegations [PEP 480] | PyPI attestations; npm and crates.io trusted publishing [crates.io update 2025-07] | All of these, with offline namespace policies, a separately keyed `claimed` role and pinned signers (D-ECO-16) | Every entry verifiable offline; no online key adds a publisher or re-delegates a namespace; first-party packages reproduced |
| Resolution and SemVer | PubGrub [PubGrub]; Rustdoc-JSON linting [cargo-semver-checks] | uv, on PubGrub [uv resolver]; Cargo's backtracking resolver [Cargo resolver] | PubGrub with typed explanations; interface, output and name diffs (D-ECO-14) | Full graph under 1 s; seeded breaks all caught, no false refusals |
| Vulnerability data | OSV 1.9.1 [OSV] | OSV.dev, RustSec, GitHub Advisory Database | OSV plus correctness advisories | Advisory-to-lockfile match under 1 h |
| Events and webhooks | CloudEvents 1.0; Standard Webhooks [Standard Webhooks spec] | Svix and the other listed implementations [Standard Webhooks] | Both, Ed25519 by default, behind PLT's egress proxy (D-ECO-12) | Reference verifiers; delivery under fault injection |
| Board exchange and ECAD migration | IDX V6 [prostep IDX]; KiCad importers | KiCad 10 [KiCad 10] | IDF and IDX readers; KiCad as an external tool (D-ECO-31) | Netlist equality and empty Gerber XOR against the source tool |
| Feature recognition | B-rep message passing [BRepNet]; rules for prismatic parts | BRepNet | Rules plus segmentation trained on licensed data, verified by rebuild | 9 of 11 NIST parts rebuilt with PMI by the phase 3 gate |
| Documentation | Diátaxis; tested reference [rustdoc doctests] | rustdoc documentation tests | Diátaxis, tested and offline (D-ECO-24) | Coverage 100%; every example builds |

Deviations, with reasons:

- Licensed translators run outside evaluation: determinism and portability.
- Wasm components are CPU-only: no deterministic, portable GPU interface exists for sandboxed code.
- No 64-bit memories, and HDF5 formats wrap the C library: maturity.

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Standing |
| --- | --- | --- | --- |
| Native CAD import | CAD Exchanger reads CATIA V5, NX, Creo and SOLIDWORKS, and reads and writes Parasolid and JT [CAD Exchanger formats] | Licensed MCAD translators, 2 | Equal: the same SDK class, with each translation signed, pinned and qualified per version |
| IGES read | SolidCraft, an AI-built clone, imports IGES beside STEP [SolidCraft] | IGES read, 1 | Equal |
| DXF and DWG | CADCraft, an AI-built AutoCAD clone, reads and writes DXF R12 to 2018 and opens DWG through acadrust [CADCraft]; CAD Exchanger reads DWG and reads and writes DXF | Drawing writers, 1; DXF and DWG exchange, 2 | Equal on range; ahead on byte-identical output and an imported DWG that stays an editable program |
| Multi-CAD file management | Teamcenter manages AutoCAD, Inventor, CATIA, Creo, NX, Solid Edge and SolidWorks files in multi-CAD assemblies [Teamcenter MCAD] | Native CAD reference graphs, 3 | Later: reference graphs arrive in phase 3, and Crucible never edits foreign files |
| Solver deck exchange | Ansys Mechanical exports SOL 101, 103 and 109 with RBE2, RBE3, CBUSH and CONM2 [Ansys Nastran export] | Solver decks, 3 | Equal at phase 3; ahead in that imported decks run, and unmapped cards fail typed instead of vanishing |
| Modelica | Dymola builds on Modelica and its domain libraries [Dymola] | Modelica source import, 4 | Later: a declared subset, with FMUs for the rest, since no gate needs full Modelica earlier |
| ECAD migration | KiCad 10 imports Allegro, PADS and gEDA designs [KiCad 10] | ECAD migration, 3 | Equal: Crucible runs KiCad's importers, then reads KiCad natively |
| AP242 semantic PMI | Commercial translators in CAx-IF rounds [CAx-IF 58J] | STEP layer 3: AP242 mapping, 1 | Equal target; ahead in validation properties written and checked on every export |

## Platform notes

| Platform | Risk | Decision |
| --- | --- | --- |
| Every Tier 1 target | Translators differing per platform | Determinized translators; byte-identical exports (ECO-O-4) |
| Windows, macOS, Linux | Licensed SDKs ship for some OS and architecture pairs only | Run where the vendor ships, else on a server; the signed External input is the same everywhere |
| Windows ARM64 | Wasmtime Tier 3 [Wasmtime tiers]; licensed SDK builds | Third-party components already out of process (D-ECO-26); ARM64 builds are a vendor criterion, and translators run on a server until one ships |
| Browsers | No native Component Model; no local tool or connector context; WebRTC outside CSP's fetch directives | One runtime (D-ECO-10); third-party evaluation components remote until the bridge and exfiltration cases pass per engine; imports upload bytes to the CAS first, so Asset hashes match desktop |
| iPadOS (Tier 2) | Guidelines 2.5.2, 3.2.2(i) and 4.7 [App Review] | WKWebView shell; first-party components in the app; registry components remote |
| Android (Tier 2) | Wasmtime Tier 3; Play's downloaded-code rule [Google Play DNA] | No world imports Android APIs; PLT funds upstream coverage |
| Air-gapped installs | No Sigstore, public registry or licence servers | Offline bundles with a private root and `cosign sign --key`; offline activation as a vendor criterion; offline entitlements |
| Text inside files | Encodings and normalization differ | Decode per the declared encoding, normalize names to NFC, keep original bytes |

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| ANV | `crucible:ops/anvil` bindings generated from its catalog; licence proof per model for the ABC subset; named receiver profiles for `exchange_form` | WIT package; hash list; `ReceiverProfile` | 0 (ABC), 1 |
| FLX, COV | `crucible:ops/flux` bindings; hosting for solver and constitutive components; FMU packaging; Field, CGNS, Exodus, VTKHDF and OpenFOAM codecs; Nastran, Abaqus and LS-DYNA readers and Nastran, DMIG and OP4 writers; IFC, GDSII, OASIS, MatML and ISO 10303-235 codecs; package metadata for the coverage map | WIT package; `Mesh` Body; `Field`; Package | 2 to 5 per format |
| MEC | AP242 and QIF translators; IGES read; PDF, SVG, PDF/A, DXF and DWG writers and readers; GDSII and OASIS writers; `crucible::standards::` Packages and their licence rule; receiver profiles for `export_resolution`; IDF and STEP board readers; IFC 4.3 | `Imported`; `File`; Package | 1, 2 (DWG, boards), 5 (GDSII, IFC) |
| MFG | Every `io/` writer MFG's outputs use (3MF, IPC-2581, Gerber, IPC-D-356, ODB++, QIF, STEP-NC, USD, ISO 13399); QIF Results and CSV import; machine-definition sources; ERP and MES connector worlds mapped per `Site`; NC and tool-data migration | `File`; External input; `crucible:connect` | 1, 2, 3 (sites) |
| ELX | Board and harness readers and writers; ECAD migration through KiCad 10; the Modelica reader; `parts::` publishing with its data-licence rule; the offer, lifecycle and change-notice feeds | `File`; `Network`; Package; External input | 2 to 4 |
| KLN | Determinized binary hashes for node keys; event envelope and delivery; ERP, MES and PLM connectors; the software supply chain; feeds as signed External inputs; the HMAC watermark transform; reference graphs of native CAD files for `Document` Items; part lifecycle events for the obsolescence check | Event; External input; `File` | 1, 3 (watermark, reference graphs, lifecycle) |
| ING | Registry and signing; interface diffs; determinized components; the RFC process; PubGrub resolution with typed explanations | Package; lockfile entries | 0 |
| AGT | Catalog entries for ECO's methods; registry, event and archive behaviour; importers returning `ExternalText`; licence metadata; partner connectors; `release_data` members for every exit to another party; CLI exit codes | API method; Act kind; `ExternalText` | 1 |
| UIX | The registry with metadata, capability descriptions and badges; `TranslationReport`s; font packages; licensed translators as external tools | Package; `TranslationReport` | 1 |
| PLT | Worlds to enforce; declared memory limits; component descriptions; the sandbox site's policy including `webrtc 'block'`; font packages; the licence allowlist; export classification, the restricted-jurisdiction dataset for update servers and CRA reporting; webhook address rules for the egress proxy | WIT world; policy records | 1, 2 (browser sandbox) |

Outside users get the SDKs, C ABI, CLI, webhooks, and the archive and CAS encoding specifications.

## Oracles

ECO's oracles live in `oracles/eco/`, readable but not writable by agents. Each has a held-out split outside the agent-readable tree (contract section 3, principle 6). Corpus oracles (1 to 3, 15 to 17, 21, 23 to 26, 32, 36 to 38) hold out files by a keyed hash. Generated-input oracles (5, 7 to 10, 14, 18 to 20, 28 to 31, 33 to 35) draw seeds at CI time. Golden-product oracles (4, 6, 11 to 13, 22, 27) add variants with perturbed parameters.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| ECO-O-1 | STEP readers: validation properties against Anvil's values on every corpus file | All within production thresholds; 95% within 0.05% on volume and area (target) |
| ECO-O-2 | Semantic PMI export and import on the NIST CTC, FTC, STC and HTC cases | Every item equal in type, value, tolerance, datums and targets; facet-face controls presentation-only |
| ECO-O-3 | Exported files: generated EXPRESS rules, NIST SFA, XSD and consortium validators | Zero errors |
| ECO-O-4 | Export determinism: every golden product in every format on every Tier 1 platform, and the run build's AP242 and 3MF from the gate release | Byte-identical Files |
| ECO-O-5 | Readers under structure-aware and grammar-based fuzzing | No panic, no allocation beyond limits, termination within fuel; 10⁹ executions per release without a new crash (target) |
| ECO-O-6 | Engine identity: 10⁴ vectors per first-party component on Wasmtime (x86-64, ARM64), JavaScriptCore, V8 and SpiderMonkey, with `crucible:ops` answered in and out of process and out of order; rerun before any engine upgrade | Identical outputs, host-call sequences and trap points |
| ECO-O-7 | Determinization: publish-time runs on two code-free hosts, build-time runs and install-time re-runs with one determinizer version, and a substituted uninstrumented binary | Byte-identical binaries and matching receipts; forbidden features refused with offsets; the substituted binary refused at install |
| ECO-O-8 | Isolation: red-team components reaching forbidden imports, undeclared hosts, foreign directories, secrets, labelled reads plus egress, a hard-coded confidential `ObjectId` and worker credentials; a native guest trying DNS, TCP, UDP and HTTP egress; browser-sandbox code trying `fetch`, WebSocket, `importScripts`, navigation, `RTCPeerConnection`, DNS prefetch and `<link rel=preconnect>`, in every Tier 1 browser engine | Every attempt refused, typed and audited; workers hold no tokens, handles or keys; an engine that fails evaluates third-party components remotely |
| ECO-O-9 | Registry integrity: altered bytes, rollback, freeze, mix-and-match, split views, forged provenance, an online key adding a publisher or re-delegating a claimed namespace, an unwarned recently claimed namespace, signer changes, a lapsed domain re-registered by a stranger, unlisted namespaces, a root below threshold, an expired `claimed` role | Every case detected; the lapsed namespace frozen; rebuilt first-party hashes equal published ones |
| ECO-O-10 | Compatibility gates: seeded breaks, output changes and entity renames in minors and patches | Breaks refused; changes labelled |
| ECO-O-11 | SDKs and C ABI: AGT golden transcripts through every SDK; ABI symbol diff | Byte-identical canonical JSON; no symbol removed in a major |
| ECO-O-12 | Exit: an independent reader in another language, built from the specifications, reads golden-product archives | Same Changes, Body measurements within bounds, same BOM |
| ECO-O-13 | Edition migration on every golden product and registry test design | Identical output hashes |
| ECO-O-14 | Webhooks under outages, failing receivers, duplicates, DNS rebinding, redirects and SSRF probes into private, CGNAT, unique-local and IPv4-mapped ranges | At least once, deduplicated, ordered, signed; probes and 3xx refused; no `ObjectId` or file hash in a payload above `public` |
| ECO-O-15 | Licensed translator qualification per pinned version, including the reference graph of native assemblies | Record reproduces; thresholds met or the version flagged; every referenced file and configuration matches the source |
| ECO-O-16 | Every catalog row on its conformance suite (3MF with and without beam lattices, Reference FMUs, SSP, IFC, KiCad, Gerber re-reading, QIF Results and CSV import, IGES, machine-definition sources, tool data within 1 µm) | Every row at or below the current phase passes |
| ECO-O-17 | Nothing lost: source entities counted by kind against report entries, per corpus and bulk-import file | Every entity accounted for |
| ECO-O-18 | Untrusted content: injections in names, PMI, notes, metadata, READMEs, embossed text and textures (shared with AGT) | No string reaches an identifier or agent context except as `ExternalText`; unendorsed derived Bodies carry `data_untrusted` |
| ECO-O-19 | Resolution and holds: `crucible add` and `crucible update` traced; a version fixing a self-filed advisory; a version fixing an independent advisory through the trusted publisher | No package code runs; the self-filed fix waits out the hold; the independent fix resolves with a flag |
| ECO-O-20 | Paid packages offline with valid, expired and revoked entitlements | Pinned designs always rebuild; unentitled new versions blocked |
| ECO-O-21 | Reconstruction and source translation on NIST parts and a held-out prismatic set | 9 of 11 NIST parts and 80% of the set within 1 µm with all PMI by the phase 3 gate (target) |
| ECO-O-22 | Re-export of archived golden-product releases from every earlier stable and LTS release | Byte-identical to the archived Files |
| ECO-O-23 | Part 21 layer: read then write every corpus file; dictionary-driven against generated access; the fallback build from a pinned schema hash | Every instance reproduced; equal values; the fallback binary hash equals the published one |
| ECO-O-24 | Round trips in normal form: self round trips and Open CASCADE differential reads | The suites' pass lines; every disagreement triaged |
| ECO-O-25 | Board writers and ECAD migration on open EAGLE, Altium, Allegro, PADS and KiCad designs and Crucible boards | Netlists equal the source tool's; Gerber XOR empty; ODB++ matches KiCad's writer |
| ECO-O-26 | Board exchange: KiCad's IDF and STEP exports of an open board | Outline, holes, keep-outs, heights and reference designators equal the source |
| ECO-O-27 | Connectors against a mock ERP, MES and PLM, replaying every event, with a release whose plan carries ERP and MES effects, two `Site`s with different routings for one EBOM, and a catalog feed announcing an end of life and a change notice | Idempotent; field ownership kept; effects delivered under one Approval and retried; external approvals pinned as records only; both sites reconcile; lifecycle updates land only on the monitoring branch |
| ECO-O-28 | Every exit path with and without an approved `release_data` plan, and a standing release given an over-ceiling payload | Nothing leaves without one; label, screening, authorization and ceiling failures refuse the commit |
| ECO-O-29 | Compliance: labelled, unattested or unclassified packages; a DSA notice of controlled content; parties, buyers and update clients established in each restricted jurisdiction; escrow scans; an exploited-vulnerability drill; a notice through to its statement of reasons; a phase 1 release without the liability assessment | Refused, quarantined or flagged; CRA reports drafted within 24 h and 72 h; every removal has a statement of reasons; the release blocked |
| ECO-O-30 | Contributions: an external one without `Signed-off-by`; an agent-written commit with `Signed-off-by`, without `Assisted-by` or without a founder `Reviewed-by`; seeded copyleft snippets; a permissive snippet without its notice; a snippet split across small undeclared commits | Every case blocks the merge; a permissive snippet with its notice passes |
| ECO-O-31 | Licence policy on every distribution and corpus: contract section 7.7's list, notices, source offers, standards tables, `parts::` data licences, machine-definition licences, corpus licence proofs | No disallowed licence; every notice and offer present; no corpus item without a licence proof |
| ECO-O-32 | Documentation and certification | Every example builds; coverage 100%; graders agree with reference solutions |
| ECO-O-33 | Watermarks: several recipients; a recipient forging another's mark; a STEP file re-saved and a 3MF re-sliced | Each unmodified file identifies its recipient with the tenant's key; forgery fails without the key; the re-exported files report as untraceable; definitional geometry and attributes unchanged |
| ECO-O-34 | ECO's published WIT packages against their tables, and every first-party package through `wasm-tools component wit` | Every listed interface, type and failure present; nothing else in a stable gate; every package parses |
| ECO-O-35 | Receiver profiles: a part with a 3 nm sliver face and a 10 µm tolerant edge exported under `parasolid`; a fillet with a profile tolerance exported as a B-spline approximation | The sliver merged or refused with `BelowReceiverResolution`; the tolerant edge reported; the approximation within 1% of the fillet's tolerance |
| ECO-O-36 | DXF and DWG: held-out drawings of every supported version read and written; Crucible drawing sheets written as DXF | Entity counts and geometry equal LibreDWG's and acadrust's readings within tolerance; re-read files equal the source; Crucible's DXF byte-identical across platforms |
| ECO-O-37 | Solver decks: NAFEMS and FLX test decks read from Nastran, Abaqus and LS-DYNA; studies written as Nastran bulk data, DMIG and OP4 | Every card read equal to pyNastran's or meshio's reading; unmapped cards reported with line numbers; written decks re-read by pyNastran to the same model |
| ECO-O-38 | Modelica: the MSL's `Modelica.Electrical`, `Mechanics.Rotational`, `Mechanics.Translational` and `Thermal.HeatTransfer` examples | Translated models match the MSL reference results within their tolerances; untranslated constructs reported |

## Phasing

| Phase | ECO contribution to the gate |
| --- | --- |
| 0 | ECO-O-6 and ECO-O-7's publish-time and build-time cases green in the determinism suite; `crucible:` packages at 0.x, ECO's own specified (ECO-O-34); names cleared and `crucible-sdk` reserved on every index; ISO's permission requested and STEP layer 1 from hash-pinned schemas with its deterministic fallback; licence and contribution checks; counsel's authorship and thread-table opinions; the stewardship trigger, trademark option and key ceremony; Rust SDK |
| 1 | GP1: AP242 with geometry, structure, validation properties and semantic PMI passing ECO-O-1 to ECO-O-4 under the shop's receiver profile, in a release bundle; QIF Results and CSV import of external metrology. GP2: 3MF with beam lattices marked required, plus a Core mesh, passing consortium validation and the bureau's file-acceptance test. The gate release reproduces the run build's AP242 and 3MF (ECO-O-4). Also drawings with DXF sheets, IGES, AP203 and AP214 read, STL, re-import matching, the first-party index, the first CAx-IF round, the Python SDK, CLI, webhooks, archive, docs, export classification, CRA reporting and the product-liability assessment |
| 2 | GP3 and GP4 exchanged with an external CAD system by AP242 round trip with persistent ids; GP3's legacy programs and tool libraries imported and its machines defined from builder sources; GP4's flat patterns as DXF. Also DXF and DWG exchange, licensed translators, board exchange, the public registry with notices and moderation, standing releases, connectors, the browser sandbox once the bridge passes, the TypeScript SDK, the C ABI and dual signatures |
| 3 | GP5's board fabricated and assembled from Crucible's Gerber X2, XNC, IPC-2581C or ODB++ and placement outputs; GP5's drop model read from LS-DYNA keywords; Nastran and Abaqus decks that run, with BDF, DMIG and OP4 export; FMU import (contract section 13.4); ECAD migration; native CAD reference graphs; part lifecycle feeds; multi-site connectors; watermarks; paid packages and certified partners |
| 4 | GP6 FE and CFD models exchanged with an external solver; Modelica source import; FMU export and SSP (contract section 13.4); robot descriptions; IDX change proposals |
| 5 and later | GP8 round-tripped through IFC 4.3; AP239 and AP233; GP14's IFC export in phase 7 |

## Open questions

1. **Translator vendor.** The choice among CAD Exchanger, HOOPS Exchange and Datakit waits on terms only negotiation reveals: server use, unlicensed rebuilds, ARM64 builds, offline activation and reference-graph extraction. The founder signs the first agreement before the phase 2 gate.
2. **Open-source downloads under EU sector rules.** Whether public open-source downloads need the authorisation route of Article 5n(9b) of Regulation (EU) 833/2014 waits on counsel's opinion; until it arrives, the public registry geo-restricts the restricted jurisdictions like the update servers.
3. **ODB++ partnership terms.** Whether the ODB++ writer ships in-tree waits on counsel reading the partnership terms before the phase 3 writer starts; if they forbid Apache-2.0, the writer ships as an external tool.

## Contract change requests

None.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [15 CFR 742.15] | 15 CFR 742.15, encryption items | https://www.law.cornell.edu/cfr/text/15/742.15 | 2026-10-11 |
| [15 CFR 746] | 15 CFR part 746, embargoes and other special controls | https://www.law.cornell.edu/cfr/text/15/part-746 | 2026-10-12 |
| [15 CFR 746.8] | 15 CFR 746.8, sanctions against Russia and Belarus | https://www.law.cornell.edu/cfr/text/15/746.8 | 2026-10-11 |
| [15 USC 1060] | 15 U.S.C. 1060, assignment of marks | https://www.law.cornell.edu/uscode/text/15/1060 | 2026-10-11 |
| [15 USC 1127] | 15 U.S.C. 1127, definitions, abandonment | https://www.law.cornell.edu/uscode/text/15/1127 | 2026-10-11 |
| [17 USC 512] | 17 U.S.C. 512, designated agent and repeat infringers | https://www.law.cornell.edu/uscode/text/17/512 | 2026-10-11 |
| [3MF beam lattice] | 3MF Beam Lattice Extension 1.2.0 | https://github.com/3MFConsortium/spec_beamlattice/blob/master/3MF%20Beam%20Lattice%20Extension.md | 2026-10-11 |
| [3MF core] | 3MF Core Specification | https://github.com/3MFConsortium/spec_core/blob/master/3MF%20Core%20Specification.md | 2026-10-11 |
| [3MF specifications] | 3MF specifications | https://3mf.io/spec/ | 2026-10-11 |
| [ABC] | ABC dataset | https://deep-geometry.github.io/abc-dataset/ | 2026-10-11 |
| [acadrust] | acadrust crate documentation, version 0.6.4 | https://docs.rs/crate/acadrust/latest | 2026-10-12 |
| [AMF wiki] | Additive manufacturing file format | https://en.wikipedia.org/wiki/Additive_manufacturing_file_format | 2026-10-11 |
| [Ansys Nastran export] | Ansys Mechanical 2024 R2 help, NASTRAN export supported features | https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html | 2026-10-12 |
| [AOUSD core 1.0] | OpenUSD Core Specification 1.0 release | https://digitalproduction.com/2026/01/05/aousd-releases-openusd-core-specification-1-0/ | 2026-10-11 |
| [Apache-2.0] | Apache License 2.0 | https://www.apache.org/licenses/LICENSE-2.0 | 2026-10-11 |
| [App Review] | Apple App Review Guidelines | https://developer.apple.com/app-store/review/guidelines/ | 2026-10-11 |
| [Atlassian Crucible] | Atlassian Crucible product page | https://www.atlassian.com/software/crucible | 2026-10-11 |
| [Atlassian trademarks] | Atlassian trademark list | https://www.atlassian.com/legal/trademark | 2026-10-11 |
| [B2MML] | MESA B2MML, the XML implementation of ISA-95 | https://github.com/MESAInternational/B2MML-BatchML | 2026-10-11 |
| [BRepNet] | BRepNet, arXiv 2104.00706 | https://arxiv.org/abs/2104.00706 | 2026-10-11 |
| [build123d] | build123d repository | https://github.com/gumyr/build123d | 2026-10-11 |
| [buildingSMART IFC 4.3] | IFC 4.3 published as ISO standard | https://www.buildingsmart.org/?p=29521 | 2026-10-11 |
| [CAD Exchanger formats] | CAD Exchanger supported formats | https://cadexchanger.com/formats/ | 2026-10-11 |
| [CADCraft] | CADCraft repository README | https://github.com/storytold/cadcraft | 2026-10-12 |
| [CadQuery] | CadQuery repository | https://github.com/CadQuery/cadquery | 2026-10-11 |
| [Cargo resolver] | Cargo dependency resolution | https://doc.rust-lang.org/cargo/reference/resolver.html | 2026-10-11 |
| [cargo yank] | cargo yank | https://doc.rust-lang.org/cargo/commands/cargo-yank.html | 2026-10-11 |
| [cargo-semver-checks] | cargo-semver-checks | https://github.com/obi1kenobi/cargo-semver-checks | 2026-10-11 |
| [CAx-IF 58J] | CAx-IF Round 58J test suite, v1.1 | https://www.mbx-if.org/home/wp-content/uploads/2026/08/test_suite_58j_v11.pdf | 2026-10-11 |
| [CAx-IF GVP] | CAx-IF Recommended Practices for Geometric and Assembly Validation Properties, v4.6 | https://www.mbx-if.org/documents/rec_prac_gvp_v46.pdf | 2026-10-11 |
| [CGNS releases] | CGNS releases | https://github.com/CGNS/CGNS/releases | 2026-10-11 |
| [CloudEvents] | CloudEvents specification | https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md | 2026-10-11 |
| [CloudEvents sequence] | CloudEvents sequence extension | https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/sequence.md | 2026-10-11 |
| [CM concurrency] | Component Model concurrency explainer | https://github.com/WebAssembly/component-model/blob/main/design/mvp/Concurrency.md | 2026-10-11 |
| [Component Model] | WebAssembly Component Model repository | https://github.com/WebAssembly/component-model | 2026-10-11 |
| [Contributor Covenant] | Contributor Covenant | https://www.contributor-covenant.org/ | 2026-10-11 |
| [Copyright Office 2025] | US Copyright Office, Copyright and Artificial Intelligence, Part 2: Copyrightability, January 2025 | https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf | 2026-10-12 |
| [cosign key signing] | Sigstore, signing with a key pair | https://docs.sigstore.dev/cosign/signing/signing_with_containers/ | 2026-10-11 |
| [CRA] | Regulation (EU) 2024/2847, the Cyber Resilience Act | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402847 | 2026-10-11 |
| [crates.io crucible] | crates.io record for `crucible` | https://crates.io/api/v1/crates/crucible | 2026-10-11 |
| [crates.io crucible-sdk] | crates.io lookup for `crucible-sdk` (not found) | https://crates.io/api/v1/crates/crucible-sdk | 2026-10-11 |
| [crates.io update 2025-07] | crates.io development update, July 2025 | https://blog.rust-lang.org/2025/07/11/crates-io-development-update-2025-07/ | 2026-10-11 |
| [Crucible game] | Crucible (video game) | https://en.wikipedia.org/wiki/Crucible_(video_game) | 2026-10-11 |
| [Datakit] | Datakit home | https://www.datakit.com/en/ | 2026-10-11 |
| [DCO] | Developer Certificate of Origin 1.1 | https://developercertificate.org/ | 2026-10-11 |
| [DFARS 7012] | DFARS 252.204-7012, safeguarding covered defense information and cyber incident reporting | https://www.acquisition.gov/dfars/252.204-7012-safeguarding-covered-defense-information-and-cyber-incident-reporting. | 2026-10-11 |
| [Directive 96/9/EC] | Directive 96/9/EC on the legal protection of databases | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:31996L0009 | 2026-10-11 |
| [Diátaxis] | Diátaxis | https://diataxis.fr/ | 2026-10-11 |
| [DMCA directory] | US Copyright Office, DMCA designated agent directory | https://www.copyright.gov/dmca-directory/ | 2026-10-11 |
| [DSA] | Regulation (EU) 2022/2065, the Digital Services Act | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R2065 | 2026-10-11 |
| [Dymola] | Dassault Systèmes, CATIA Dymola product page | https://www.3ds.com/products/catia/dymola | 2026-10-12 |
| [EAGLE] | EAGLE (program), citing Autodesk's announcement of the end of sales and support | https://en.wikipedia.org/wiki/EAGLE_(program) | 2026-10-11 |
| [EC product liability] | European Commission, liability for defective products | https://single-market-economy.ec.europa.eu/single-market/goods/free-movement-sectors/liability-defective-products_en | 2026-10-12 |
| [EDIF wiki] | EDIF | https://en.wikipedia.org/wiki/EDIF | 2026-10-11 |
| [espr] | espr EXPRESS compiler documentation | https://docs.rs/espr/latest/espr/ | 2026-10-11 |
| [espr crates.io] | crates.io API record for `espr` | https://crates.io/api/v1/crates/espr | 2026-10-11 |
| [EU 833/2014] | Regulation (EU) 833/2014, consolidated text of 20 July 2025, Article 5n | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02014R0833-20250720 | 2026-10-11 |
| [EU VAT 1042/2013] | Implementing Regulation (EU) 1042/2013, Article 9a of Regulation 282/2011 | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013R1042 | 2026-10-11 |
| [FDA CSA] | FDA, Computer Software Assurance for Production and Quality Management System Software | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-management-system-software | 2026-10-11 |
| [finite-wasm] | finite-wasm | https://github.com/near/finite-wasm | 2026-10-11 |
| [FIPS 204] | FIPS 204, Module-Lattice-Based Digital Signature Standard | https://csrc.nist.gov/pubs/fips/204/final | 2026-10-11 |
| [Flux AI] | Flux home page | https://www.flux.ai/ | 2026-10-11 |
| [FMI 3.0.2 news] | FMI 2.0.5 and 3.0.2 released | https://fmi-standard.org/news/2024-11-27-fmi-2.0.5-and-3.0.2 | 2026-10-11 |
| [FMI site] | FMI Standard home | https://fmi-standard.org/ | 2026-10-11 |
| [fmi-ls-wasm] | FMI-LS-WASM prototype | https://github.com/modelica/fmi-ls-wasm | 2026-10-11 |
| [Fusion 360 Gallery licence] | Fusion 360 Gallery Dataset licence | https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md | 2026-10-11 |
| [Gerber wiki] | Gerber format | https://en.wikipedia.org/wiki/Gerber_format | 2026-10-11 |
| [Google Play DNA] | Google Play Device and Network Abuse policy | https://support.google.com/googleplay/android-developer/answer/9888379?hl=en | 2026-10-11 |
| [HDF5 track times] | HDF5 object creation properties, `H5Pset_obj_track_times` | https://support.hdfgroup.org/documentation/hdf5/latest/group___o_c_p_l.html | 2026-10-11 |
| [HOOPS Exchange] | HOOPS Exchange product page | https://www.techsoft3d.com/products/hoops/exchange/ | 2026-10-11 |
| [IGES wiki] | IGES | https://en.wikipedia.org/wiki/IGES | 2026-10-11 |
| [IPC-2581C] | IPC-2581 Revision C release | https://www.electronics.org/news-release/ipc-releases-ipc-2581-revision-c-generic-requirements-printed-board-assembly-products | 2026-10-11 |
| [ISO 10303 portal] | ISO standards portal for ISO 10303, notice on electronic inserts | https://standards.iso.org/iso/10303/ | 2026-10-11 |
| [ISO 10303 wiki] | ISO 10303 overview of application protocols | https://en.wikipedia.org/wiki/ISO_10303 | 2026-10-11 |
| [ISO 14306] | ISO 14306-1:2024, JT | https://committee.iso.org/standard/86063.html?browse=ics | 2026-10-11 |
| [ISO 16739] | ISO 16739-1:2024, IFC | https://www.iso.org/standard/84123.html | 2026-10-11 |
| [ISO 242] | ISO 10303-242:2025, edition 4 | https://www.iso.org/standard/84300.html | 2026-10-11 |
| [Jackson 1995] | D. J. Jackson, Boundary representation modelling with local tolerances, 1995 | https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf | 2026-10-12 |
| [jco] | jco | https://github.com/bytecodealliance/jco | 2026-10-11 |
| [KCL docs] | KCL language documentation | https://zoo.dev/docs/kcl-lang | 2026-10-11 |
| [Khronos glTF ISO] | glTF 2.0 as ISO/IEC 12113:2022 | https://www.khronos.org/news/press/khronos-gltf-2.0-released-as-an-iso-iec-international-standard | 2026-10-11 |
| [KiCad 10] | KiCad 10.0.0 release announcement | https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/ | 2026-10-12 |
| [KiCad 9 docs] | KiCad 9 documentation, importing non-KiCad projects | https://docs.kicad.org/9.0/en/kicad/kicad.html | 2026-10-11 |
| [KiCad 9 PCB editor] | KiCad 9 PCB editor documentation | https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html | 2026-10-11 |
| [KiCad 9.0] | KiCad 9.0.0 release announcement | https://www.kicad.org/blog/2025/02/Version-9.0.0-Released/ | 2026-10-11 |
| [KiCad formats] | KiCad file formats | https://dev-docs.kicad.org/en/file-formats/ | 2026-10-11 |
| [KiCad library licence] | KiCad library licence | https://www.kicad.org/libraries/license/ | 2026-10-11 |
| [KiCad licences] | KiCad licences | https://www.kicad.org/about/licenses/ | 2026-10-11 |
| [Kiln FogBugz] | FogBugz help centre, general information on Kiln and version control products | https://fogbugz.kayako.com/article/55180-general-information-kiln-and-version-control-products | 2026-10-12 |
| [LF generative AI] | Linux Foundation policy on generative AI contributions | https://www.linuxfoundation.org/legal/generative-ai | 2026-10-11 |
| [lib3mf] | lib3mf repository and licence | https://github.com/3MFConsortium/lib3mf | 2026-10-11 |
| [LLVM exception] | SPDX LLVM-exception | https://spdx.org/licenses/LLVM-exception.html | 2026-10-11 |
| [Maven Central namespaces] | Maven Central namespace registration | https://central.sonatype.org/register/namespace/ | 2026-10-11 |
| [MBx-IF] | MBx Interoperability Forum home | https://www.mbx-if.org/home/ | 2026-10-11 |
| [MDN connect-src] | MDN, CSP `connect-src` | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src | 2026-10-11 |
| [MDN script-src] | MDN, CSP `script-src` and `'wasm-unsafe-eval'` | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src | 2026-10-11 |
| [meshio] | meshio repository README | https://github.com/nschloe/meshio | 2026-10-12 |
| [Modelica newsletter 2026-02] | Modelica Association newsletter | https://modelica.org/newsletter/2026-02 | 2026-10-11 |
| [MPL FAQ] | MPL 2.0 FAQ | https://www.mozilla.org/en-US/MPL/2.0/FAQ/ | 2026-10-11 |
| [MPL-2.0] | Mozilla Public License 2.0 | https://www.mozilla.org/en-US/MPL/2.0/ | 2026-10-11 |
| [MSL] | Modelica Standard Library repository, v4.1.0 | https://github.com/modelica/ModelicaStandardLibrary | 2026-10-12 |
| [MTConnect 2.5.0] | MTConnect Standard Part 1, version 2.5.0 | https://docs.mtconnect.org/MBSD_MTConnect_Part_1_2-5-0.pdf | 2026-10-11 |
| [NIST MBE PMI] | NIST MBE PMI validation and conformance testing | https://www.nist.gov/ctl/smart-connected-systems-division/smart-connected-manufacturing-systems-group/mbe-pmi-0 | 2026-10-11 |
| [npm crucible-sdk] | npm lookup for `crucible-sdk` (not found) | https://registry.npmjs.org/crucible-sdk | 2026-10-11 |
| [npm security plan] | GitHub's plan for a more secure npm supply chain | https://github.blog/security/supply-chain-security/our-plan-for-a-more-secure-npm-supply-chain/ | 2026-10-11 |
| [npm unpublish] | npm unpublish policy | https://docs.npmjs.com/policies/unpublish | 2026-10-11 |
| [OAGi] | Open Applications Group, OAGIS | https://oagi.org/ | 2026-10-11 |
| [OCCT licence] | Open CASCADE Technology licensing | https://occt3d.com/open-cascade-technology/index.html | 2026-10-11 |
| [OCCT releases] | Open CASCADE Technology releases | https://github.com/Open-Cascade-SAS/OCCT/releases | 2026-10-11 |
| [OCCT shape healing] | Open CASCADE Shape Healing user guide | https://occt3d.com/dev/doc/overview/html/occt_user_guides__shape_healing.html | 2026-10-11 |
| [ODB++ 8.1] | ODB++Design 8.1 update 3 | https://odbplusplus.com/blog/design/odbdesign-newest-version-available-and-compatible-with-all-version-8-releases/ | 2026-10-11 |
| [OMG SysML v2] | OMG press release on SysML v2, KerML and the Systems Modeling API | https://www.omg.org/news/releases/pr2025/07-21-25.htm | 2026-10-11 |
| [Onshape terms] | Onshape terms of use, section 1(g)(ii) | https://www.onshape.com/en/legal/terms-of-use | 2026-10-11 |
| [OPC 40501-1] | OPC UA for Machine Tools | https://reference.opcfoundation.org/MachineTool | 2026-10-11 |
| [OPC 40501-1 v1.02] | OPC UA for Machine Tools, Part 1, release 1.02.0 | https://reference.opcfoundation.org/MachineTool/v102/docs/ | 2026-10-11 |
| [OpenFOAM 14] | OpenFOAM Foundation downloads, OpenFOAM 14 | https://openfoam.org/download/ | 2026-10-11 |
| [OpenFOAM v2606] | OpenFOAM news, v2606 | https://www.openfoam.com/news/main-news | 2026-10-11 |
| [OpenSCAD COPYING] | OpenSCAD licence file | https://raw.githubusercontent.com/openscad/openscad/master/COPYING | 2026-10-11 |
| [OpenUSD up axis] | OpenUSD, stage up axis | https://openusd.org/release/api/group___usd_geom_up_axis__group.html | 2026-10-11 |
| [OSV] | OSV schema | https://ossf.github.io/osv-schema/ | 2026-10-11 |
| [OWFa 1.0] | Open Web Foundation Final Specification Agreement 1.0 | https://www.openwebfoundation.org/the-agreements/the-owf-1-0-agreements-granted-claims/owfa-1-0 | 2026-10-11 |
| [PDF/A wiki] | PDF/A and the parts of ISO 19005 | https://en.wikipedia.org/wiki/PDF/A | 2026-10-11 |
| [PEP 458] | PEP 458, secure PyPI downloads with signed repository metadata | https://peps.python.org/pep-0458/ | 2026-10-11 |
| [PEP 480] | PEP 480, surviving a compromise of PyPI | https://peps.python.org/pep-0480/ | 2026-10-11 |
| [PEP 740] | PEP 740, index support for digital attestations | https://peps.python.org/pep-0740/ | 2026-10-11 |
| [prostep IDX] | ECAD/MCAD Collaboration Implementor Forum | https://www.prostep.org/en/projects/ecad/mcad-collaboration-implementor-forum | 2026-10-11 |
| [PubGrub] | PubGrub crate documentation | https://pubgrub-rs.github.io/pubgrub/pubgrub/ | 2026-10-11 |
| [Pulley] | Wasmtime Pulley interpreter | https://docs.wasmtime.dev/examples-pulley.html | 2026-10-11 |
| [pyNastran] | pyNastran repository README | https://github.com/SteveDoyle2/pyNastran | 2026-10-12 |
| [PyPI crucible] | PyPI record for `crucible` | https://pypi.org/pypi/crucible/json | 2026-10-11 |
| [PyPI crucible-sdk] | PyPI lookup for `crucible-sdk` (not found) | https://pypi.org/pypi/crucible-sdk/json | 2026-10-11 |
| [QIF site] | Digital Metrology Standards Consortium | https://qifstandards.org | 2026-10-11 |
| [ReqIF] | OMG ReqIF specification page | https://www.omg.org/spec/ReqIF | 2026-10-11 |
| [REUSE 3.3] | REUSE Specification 3.3 | https://reuse.software/spec-3.3/ | 2026-10-11 |
| [RFC 9116] | RFC 9116, security.txt | https://www.rfc-editor.org/rfc/rfc9116 | 2026-10-11 |
| [Rumoca] | Rumoca repository README | https://github.com/CogniPilot/rumoca | 2026-10-12 |
| [Rust editions] | The Rust Edition Guide, what are editions | https://doc.rust-lang.org/edition-guide/editions/index.html | 2026-10-11 |
| [rustdoc doctests] | rustdoc documentation tests | https://doc.rust-lang.org/rustdoc/write-documentation/documentation-tests.html | 2026-10-11 |
| [SDFormat] | SDFormat specification | http://sdformat.org/spec | 2026-10-11 |
| [SEACAS] | SEACAS and the Exodus library | https://github.com/sandialabs/seacas | 2026-10-11 |
| [Sigstore] | Sigstore overview | https://docs.sigstore.dev/about/overview/ | 2026-10-11 |
| [Simcenter Flux] | Siemens Simcenter Flux product page | https://www.siemens.com/en-us/products/simcenter/electromagnetics-simulation/flux/ | 2026-10-11 |
| [SLSA] | SLSA specification v1.2 | https://slsa.dev/spec/ | 2026-10-11 |
| [SLSA build track] | SLSA v1.2 build track basics | https://slsa.dev/spec/v1.2/build-track-basics | 2026-10-11 |
| [SolidCraft] | SolidCraft repository README | https://github.com/bherbruck/solvecraft | 2026-10-12 |
| [SSP site] | SSP Standard home | https://ssp-standard.org/ | 2026-10-11 |
| [Standard Webhooks] | Standard Webhooks home | https://www.standardwebhooks.com/ | 2026-10-11 |
| [Standard Webhooks spec] | Standard Webhooks specification | https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md | 2026-10-11 |
| [SVG 1.1] | Scalable Vector Graphics 1.1, Second Edition | https://www.w3.org/TR/SVG11/ | 2026-10-11 |
| [Teamcenter MCAD] | Siemens, Teamcenter MCAD design management | https://www.siemens.com/en-us/products/teamcenter/solutions/mcad-mechanical-design-management/ | 2026-10-12 |
| [TUF] | The Update Framework | https://theupdateframework.io/ | 2026-10-11 |
| [TUF spec] | The Update Framework specification | https://theupdateframework.github.io/specification/latest/ | 2026-10-11 |
| [Ucamco Gerber] | Ucamco Gerber format downloads | https://www.ucamco.com/en/gerber/downloads | 2026-10-11 |
| [uv resolver] | uv resolver internals | https://docs.astral.sh/uv/reference/internals/resolver/ | 2026-10-11 |
| [VTKHDF] | VTKHDF file format | https://docs.vtk.org/en/latest/vtk_file_formats/vtkhdf_file_format/index.html | 2026-10-11 |
| [WASI 0.3] | WASI 0.3 release notes | https://wasi.dev/releases/wasi-p3 | 2026-10-11 |
| [WASI roadmap] | WASI roadmap | https://wasi.dev/roadmap | 2026-10-11 |
| [Wasm 3.0] | Wasm 3.0 announcement | https://webassembly.org/news/2025-09-17-wasm-3.0 | 2026-10-11 |
| [wasm-instrument] | wasm-instrument documentation | https://docs.rs/wasm-instrument/latest/wasm_instrument/ | 2026-10-11 |
| [wasm-pkg-tools] | wasm-pkg-tools and `wkg` | https://github.com/bytecodealliance/wasm-pkg-tools | 2026-10-11 |
| [Wasmtime determinism] | Deterministic Wasm execution in Wasmtime | https://docs.wasmtime.dev/examples-deterministic-wasm-execution.html | 2026-10-11 |
| [Wasmtime GHSA-394w] | Wasmtime advisory GHSA-394w-hwhg-8vgm, out-of-bounds write or crash when transcoding component model strings | https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-394w-hwhg-8vgm | 2026-10-11 |
| [Wasmtime GHSA-6wgr] | Wasmtime advisory GHSA-6wgr-89rj-399p, data leakage between pooling allocator instances | https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-6wgr-89rj-399p | 2026-10-11 |
| [Wasmtime releases] | Wasmtime release process and LTS support | https://docs.wasmtime.dev/stability-release.html | 2026-10-11 |
| [Wasmtime tiers] | Wasmtime platform support tiers | https://docs.wasmtime.dev/stability-tiers.html | 2026-10-11 |
| [WIT gates] | Component Model WIT specification, feature gates | https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md | 2026-10-11 |
| [WIT guide] | WIT reference in the Component Model book | https://component-model.bytecodealliance.org/design/wit.html | 2026-10-11 |
