# Absorbing existing software: an inventory and a safe way to do it

Research digest for round 4, 12 October 2026. Scratch under `docs/build/`; nothing here is binding until a tab or the contract adopts it.

It inventories existing software that could let Crucible go further, faster, and sets out how to use each piece within contract 7.7. Every licence below was read on the project's own page (or its LICENSE file) on 12 October 2026, unless marked [unverified]. "Tab" names the owner; "Phase" follows contract 13.1, 13.2 and 13.4 or the tab's own row.

How each piece may be used, under contract 7.7:

- **Link.** The licence is on the allowlist (MIT, MIT-0, Apache-2.0, BSD, 0BSD, ISC, Zlib, BSL-1.0, CC0-1.0, Unicode-3.0). Crucible may link it, vendor it or port it, keeping the notices. It still needs a cargo-vet audit and a `deps/approved.toml` entry (D-PLT-40).
- **Link (MPL).** Crucible may link it, but every distribution ships the MPL notices and a source offer, and changes to MPL files are published.
- **Oracle.** Run it in `oracles/` or CI as an independent check, never linked into a shipped artifact.
- **External.** Run it as an external tool or External Op, out of process, with egress denied (7.8).
- **RFC.** The licence is not on the list, so linking needs an RFC (ECO).

## Corrections and conflicts found

Six things here change or contradict what the spec says today:

1. **deal.II is not copyleft-only.** It is dual-licensed: Apache-2.0 WITH LLVM-exception, or LGPL-2.1-or-later. Under the Apache option it is the same licence as Crucible's own code, so FLX can port from it directly. It belongs in table 1, not table 2.
2. **ECO conflicts with any reverse-engineering programme.** ECO currently says "Crucible never reverse-engineers a proprietary format" (`docs/spec/11-interop-ecosystem.md`, the manufacturing, metrology, systems and materials table). DWG and the native MCAD formats are "License" rows (D-ECO-2). Building table 3's clean-room readers, or adopting the REA protocol, needs a change request against ECO and a ruling in contract 7.7. Without that ruling, tables 3 and 5 are proposals only.
3. **pubgrub is MPL-2.0.** ING and ECO both name PubGrub. If Crucible links the `pubgrub` crate rather than reimplementing it, the MPL distribution duties apply to every build, the browser bundle included.
4. **jagua-rs is MPL-2.0.** sparrow is MIT, but jagua-rs, the collision engine it builds on, is MPL-2.0. MFG's "Adopt" of sparrow (D-MFG-9) carries the MPL duties.
5. **OpenSubdiv and OpenUSD use TOST-1.0.** Both are under the Tomorrow Open Source Technology License 1.0, which is Apache-2.0 with section 6 (trademarks) rewritten. It is not on the allowlist, so these stay oracles, as D-ANV-13 already does for OpenSubdiv. Linking either needs an RFC.
6. **Algoim has a grant-back clause.** Its licence is BSD-3-Clause plus a paragraph that grants LBNL a licence to any enhancements Crucible makes public. FLX treats it as plain BSD-3-Clause-LBNL. That is fine for a port, but the grant-back should be on record when ANV ports it.

## 1. Adopt directly (permissive)

| Software | What Crucible would take | Tab, phase | Licence (verified) | Use under 7.7 |
| --- | --- | --- | --- | --- |
| **deal.II** | Sum-factorized operator code, matrix-free multigrid and hp-adaptivity, ported into `flux-forms` and `flux-solve`; a reference for FLX's CEED rows | FLX, 1 to 2 | Apache-2.0 WITH LLVM-exception, or LGPL-2.1-or-later; take the Apache option. Files under `bundled/`, `examples/` and `tests/` carry their own SPDX tags | Link, port or vendor (the same licence as Crucible) |
| **faer** | Fast dense and sparse factorizations for the `CpuIsa` paths (already chosen) | FLX, PLT, 0 | MIT. The project has moved to Codeberg; GitHub is now a mirror | Link |
| **libCEED** | The operator-split design, backend kernels to port, and the CEED benchmark problems; there are Rust bindings | FLX, 1 | BSD-2-Clause | Link, port or oracle (named in 13.2 corpora) |
| **MFEM** | The reference for H¹, H(curl) and H(div) elements, DPG and AMR; manufactured-solution oracle | FLX, COV, 1 | BSD-3-Clause | Port or oracle (named in 13.2 corpora) |
| **PETSc** | The optional `bridges/` back end for large distributed solves | FLX, 2+ | BSD-2-Clause. Packages fetched with `--download-` keep their own licences, so a bridge build must refuse GPL ones | Link (in `bridges/`) |
| **hypre** | BoomerAMG in `bridges/`; the multigrid benchmark FLX targets | FLX, 1 to 2 | Apache-2.0 OR MIT | Link (in `bridges/`) |
| **SUNDIALS**, **SLEPc** | BDF and IDA integrators and eigen-solvers as reference implementations to port and time against | FLX, ELX, 2 to 3 | BSD-3-Clause; BSD-2-Clause | Port or oracle |
| **bempp-rs** | Boundary-element assembly (already listed as linked) | FLX, COV | BSD-3-Clause | Link |
| **Clarabel.rs** | The conic and QP solver for MPC and for constrained feeds and speeds | ELX, MFG, 3 | Apache-2.0 | Link |
| **Axom** | Generalized winding-number containment, which ANV already says it will adopt | ANV, 1 | BSD-3-Clause | Port |
| **Algoim** | Cut-cell quadrature for immersed FEM | ANV, FLX, 1 | BSD-3-Clause with an LBNL enhancements grant-back | Port; record the grant-back |
| **Geogram** | Exact predicates, arrangements and 3D Delaunay, as a reference to port and as an oracle | ANV, 0 to 1 | BSD-3-Clause | Port or oracle |
| **robust** (georust) | A Rust port of Shewchuk's adaptive predicates, as the starting point and bit-for-bit reference for D-ANV-5 | ANV, 0 | MIT OR Apache-2.0 | Link or vendor |
| **Manifold** | Mesh Boolean oracle and the bake-off baseline (D-ANV-20). A native Rust port, "manifold-rust", is reported [unverified: repository and licence not found] | ANV, 1 | Apache-2.0 | Oracle; port allowed |
| **spade** | 2D constrained Delaunay with exact predicates, for sketch regions, drawing hatches and PCB pours | ANV, MEC, ELX, 1 | MIT OR Apache-2.0 | Link |
| **iOverlay** | 2D polygon Booleans and buffering (the `geo` crate's engine), for copper pours, sheet-metal nests and slice contours | ELX, MFG, 2 to 3 | MIT OR Apache-2.0 | Link |
| **cavalier_contours** | Arc-preserving 2D offsets and Booleans, for 2.5-axis pockets, profiles and kerf offsets | MFG, 2 | MIT OR Apache-2.0 | Link |
| **IPC Toolkit** | The Incremental Potential Contact reference for FLX's phase 5 contact | FLX, COV, 5 | MIT | Port or oracle |
| **meshoptimizer** (`meshopt` crate) | Vertex, index and meshlet codecs, simplification and cluster building (UIX "Adopt") | UIX, KLN, 1 to 2 | MIT | Link |
| **wgpu**, **winit**, **AccessKit**, **Parley**, **HarfRust**, **fontations** (Skrifa), **Taffy** | The GPU layer, windowing, accessibility and the text stack (already chosen) | UIX, PLT, 1 | wgpu, AccessKit and fontations: MIT OR Apache-2.0. winit: Apache-2.0 (its `dpi` folder differs). Parley: MIT OR Apache-2.0 with MIT-only and Apache-only test files. HarfRust and Taffy: MIT | Link |
| **egui** | Not the product UI (D-UIX-3 builds its own toolkit), but a fast route to internal tools: oracle viewers, debug panels, the founder's dashboards | UIX, PLT, 0 | MIT OR Apache-2.0 | Link (in tools only) |
| **Wasmtime** | The Wasm runtime (already chosen) | PLT, ECO, 0 | Apache-2.0 WITH LLVM-exception (in the LICENSE file) | Link |
| **Loro**, **Cedar**, **Salsa**, **rowan** | The CRDT, the policy engine, the incremental model and the syntax trees (already chosen) | KLN, ING, 1 to 2 | Loro: MIT. Cedar: Apache-2.0. Salsa and rowan: MIT OR Apache-2.0 | Link |
| **pubgrub** | Version resolution | ECO, ING, 1 | MPL-2.0 | Link (MPL), or reimplement the algorithm |
| **CORE-MATH** | Correctly rounded elementary functions, wrapped by `bridges/core-math` until the Rust ports pass | PLT, 0 | MIT | Link |
| **lib3mf** | The independent 3MF reader for ECO-O-16 and GP2's file-acceptance checks | ECO, MFG, 1 | BSD-2-Clause (version 2.4.1 shown) | Oracle, or wrap as a Wasm component |
| **ngspice** (core) | SPICE3 device models, ported with attribution (ELX already does this) | ELX, 3 | Modified BSD for the core. LGPLv2 in `src/maths/KLU`, `src/tclspice.c` and `src/frontend/numparam`; GPLv2+ in `src/xspice/icm/table`; MPL-2.0 in `src/osdi` | Port BSD files only; External for the whole engine (D-ELX-25) |
| **PyBaMM**, **Cantera**, **Project Chrono**, **Palace**, **PyFR**, **FEBio**, **Capytaine** | Reference solvers and benchmark cases for COV and FLX rows | FLX, COV, ELX, 2 to 7 | PyBaMM, Cantera and Chrono: BSD-3-Clause. Palace and Capytaine: Apache-2.0. PyFR: New BSD. FEBio: MIT | Oracle; ports allowed |
| **sparrow** | 2D nesting (D-MFG-9) | MFG, 2 | MIT (but see jagua-rs) | Link |
| **jagua-rs** | Sparrow's collision engine | MFG, 2 | MPL-2.0 | Link (MPL) |
| **Renode** | Firmware-in-the-loop emulator (D-ELX-18) | ELX, 4 | MIT | External (already); linking is allowed |
| **pyNastran**, **meshio** | Independent readers of Nastran BDF and OP2 (pyNastran) and Abaqus `.inp`, Nastran, Gmsh and Exodus (meshio), as oracles for ECO's FE rows | ECO, FLX, 3 | pyNastran: BSD-3-Clause. meshio: MIT | Oracle |
| **Foxtrot** (Formlabs) | A fast Rust STEP parser and triangulator, as a throughput reference for ECO layer 1 | ECO, 1 | MIT OR Apache-2.0; a proof of concept, unmaintained | Oracle; port allowed |
| **ruststep / espr** | EXPRESS compiler (ECO already forks espr's parser) | ECO, 1 | Apache-2.0; "DO NOT USE FOR PRODUCT", per its README | Vendor or fork |
| **truck** | NURBS and B-rep crates as test vectors and a benchmark. Not the kernel: D-ANV-23 rejects it (no cellular topology, tolerances or provenance) | ANV, 1 | Apache-2.0 | Oracle; port allowed |
| **Fornjot** | Little worth taking: archived 19 June 2026, "goals were never reached" | ANV | 0BSD | Anything (0BSD) |
| **SolidCraft** (github.com/bherbruck/solvecraft, formerly SolveCraft) | A competitor to measure, not a base. It is a truck-based parametric CAD with its own sketch solver, egui and wgpu, and an MCP server. Take its MCP tool surface and benchmark parts as inputs to R19's parity review, and its clean-room contribution rules as precedent (section 5) | MEC, AGT, UIX, 1 | MIT OR Apache-2.0 ("at your option") | Link allowed; study recommended |
| **CADCraft** (github.com/storytold/cadcraft) | Its DXF reader and writer (R12 to 2018 read, R2000 write) as a candidate for ECO's phase 2 DXF row. Its 2D constraint and snap behaviour as a reference for MEC drawings | MEC, MFG, ECO, 2 | README: "dual-licensed under MIT or Apache-2.0"; the organization listing shows Apache-2.0. The ArtCraft trademarks are excluded | Link, after a provenance audit |
| **acadrust** (CADCraft's DWG library) | A pure-Rust DWG and DXF reader and writer, R12 to R2018 (version 0.6.4, 11 October 2026). It could replace ECO's licensed DWG translator at phase 3 | ECO, MEC, 3 | MPL-2.0 | Link (MPL), after a provenance audit; changes ECO's DWG strategy, so it needs a change request |
| **The other storytold Craft apps** (PhotoCraft, VectorCraft, PdfCraft, DesignCraft and others) | Little for the engine. PdfCraft and VectorCraft may hold reusable PDF and vector code for MEC's drawing writers [unverified: their crates were not inspected] | MEC, UIX | Apache-2.0 per the organization listing | Link, after a provenance audit |

**Caution on young clean-room clones.** CADCraft, SolidCraft and acadrust are months old and growing fast. None of the three says how its "clean-room" status was achieved; acadrust does not say what its DWG knowledge rests on. Before any line enters Crucible, the verifier role audits provenance: commit history, contributor terms, and absence of code from LibreDWG (GPL), ODA's SDK or Autodesk's RealDWG. This is in addition to the cargo-vet audit.

## 2. External tools and oracles only (copyleft)

| Software | What Crucible would take | Tab, phase | Licence (verified) | Use under 7.7 |
| --- | --- | --- | --- | --- |
| **Open CASCADE (OCCT)** | Differential oracle for Booleans, fillets, healing, hidden lines and STEP | ANV, MEC, ECO, 1 | LGPL-2.1 with an additional exception; version 8.0.1 | Oracle |
| **FreeCAD** | Toponaming behaviour, sketcher (planegcs) and FEM workbench cases as references | ANV, MEC, 1 to 2 | LGPL-2.1 | Oracle; never read for code, since builders write the matching features |
| **KiCad** | Importers for Altium, CADSTAR, Eagle, EasyEDA, Fabmaster, gEDA, LTspice, P-CAD, PADS and, from KiCad 10, Allegro; ODB++ writer as an oracle (D-ECO-31) | ELX, ECO, 3 | GPL-3.0 or later. Libraries are CC-BY-SA 4.0 with an exception for designs that use them | External; oracle |
| **ngspice** (whole engine) | Vendor-model execution (D-ELX-25) | ELX, 3 | See table 1 | External Op |
| **CalculiX** | Structural code-to-code checks | COV, FLX, 2 | GPL-2.0 (version 2.23) | Oracle; External Op |
| **Elmer** | Multiphysics code-to-code checks | FLX, COV, 3 to 4 | GPL-2.0 or later; ElmerGUI has a linking exception for OCCT | Oracle; External Op |
| **OpenFOAM** | CFD External Op and reference (already) | FLX, COV, 4 | GPL-3.0 | External Op |
| **Gmsh** | Mesh-quality and CAD-to-mesh comparisons | ANV, FLX, 1 to 2 | GPL-2.0 or later, with a linking exception | Oracle |
| **PrusaSlicer**, **OrcaSlicer** | Slicing hand-off and the benchmark for direct slicing (D-MFG-25, D-MFG-11) | MFG, 2 | AGPL-3.0 (both) | External; oracle |
| **LibreDWG** | Independent DWG cross-check | ECO, 3 | GPL-3.0 or later | Oracle |
| **OpenCAMLib** | Drop- and push-cutter reference for 3-axis finishing | MFG, 2 | LGPL-2.1 | Oracle |
| **Freerouting** | Autorouting baseline (ELX's target is to beat it) | ELX, 3 | GPL-3.0 | Oracle |
| **OpenVAF** | Verilog-A to OSDI reference for ELX's own front end (D-ELX-14) | ELX, 3 | GPL-3.0; code derived from rustc and rust-analyzer is MIT | Oracle; read only for the MIT parts |
| **VACASK** | Circuit-simulation speed and accuracy reference | ELX, 3 | AGPL-3.0 | Oracle |
| **fTetWild**, **Fidget**, **libfive** (kernel) | Tetrahedral meshing and implicit-evaluation benchmarks | ANV, 1 to 2 | MPL-2.0 (all three). libfive's Studio and Guile bindings are GPL-2.0 or later | Oracle today. MPL allows linking if a later decision wants it |

## 3. Clean-room interoperability targets

Every row today is "License" (D-ECO-2) or absent. A row becomes "Build" only after the ECO change request in "Corrections and conflicts found" is ruled. "Published or open" lists what an implementer may read without any reverse engineering.

| Format | What Crucible would take | Tab, phase | Published or open | Use under 7.7 and the route |
| --- | --- | --- | --- | --- |
| **DWG** | Read and write of 2D drawings and flat patterns | ECO, MEC, MFG, 3 | ODA's *Open Design Specification for .dwg files* v5.4.1 (R13 to R2018; free download, "for informational use only", © ODA). Open readers: ACadSharp (MIT, C#), acadrust (MPL-2.0, Rust), LibreDWG (GPL-3.0+). Autodesk RealDWG is the commercial SDK [unverified: page refused] | Build from the ODA spec, with ACadSharp and LibreDWG as oracles, or adopt acadrust (table 1). No decompilation is needed |
| **Parasolid x_t / x_b** | Exact B-rep read and write for exchange with NX, SOLIDWORKS, Solid Edge and Onshape | ANV, ECO, 2 to 3 | A "Parasolid XT Format Reference" (2006) circulates on third-party hosts [unverified: not opened]. Siemens' current documentation is licensed to developers [unverified]. Siemens recommends x_b over x_t as more stable (Siemens support note, per search) [unverified] | Licensed SDK first (D-ECO-2). Build only from a document Siemens publishes or permits; observe files, never the kernel |
| **SOLIDWORKS .sldprt / .sldasm** | Structure, configurations, custom properties, PMI | ANV, MEC, 2 | SOLIDWORKS API and Document Manager API (vendor SDKs; the help page did not render) [unverified]. No public format specification found | Licensed SDK, or the founder's licensed copy as an external exporter. A clean-room reader only if counsel signs off (section 5) |
| **NX .prt, Creo .prt, CATIA .CATPart, Inventor .ipt, Fusion .f3d** | Structure, exact geometry, PMI | ANV, MEC, 2 to 3 | No public specifications found. Vendor SDKs exist (NX Open, Creo Toolkit, CAA, Inventor API, Fusion API) [unverified: not opened]. Commercial translators: CAD Exchanger, HOOPS Exchange, Datakit (ECO's sources) | Licensed translators (D-ECO-2). These formats wrap the vendors' kernels, so decompiling them would approach kernel algorithms, which section 5 forbids |
| **JT** | Visualization, structure, B-rep and PMI | ANV, 2 to 4 | ISO 14306-1:2024 (cited in ECO) | Build from the standard (ECO already plans this for phase 4) |
| **Altium .SchDoc / .PcbDoc / libraries** | ECAD migration | ELX, ECO, 3 | Containers are OLE Compound File Binary. KiCad's developer docs have an Altium format reference (GPL code, but documentation is readable). Community notes: python-altium `format.md`, pyaltiumlib docs, altium.js. Altium publishes no specification | Migrate through KiCad as an External (D-ECO-31). A native reader may be built from KiCad's *format documentation* and sample files, never from KiCad's code |
| **Allegro .brd** | ECAD migration | ELX, 4 | KiCad 10 reads versions 16 to 23. Its importer was "reverse-engineered from the binary structure without using any Allegro programs or libraries", from hundreds of sample files | External through KiCad. KiCad's method, file-only analysis, is the model for section 5's observer |
| **Eagle .sch / .brd** | ECAD migration | ELX, 3 | XML (KiCad import table); DTD shipped with Eagle [unverified] | Build from the XML and DTD |
| **PADS, CADSTAR, EasyEDA, P-CAD, Fabmaster** | ECAD migration | ELX, 3 to 4 | Text formats: PADS ASCII, CADSTAR S-expression archives, EasyEDA JSON | Through KiCad as an External; native readers built from samples |
| **Nastran bulk data (BDF) and OP2** | FE model and result exchange | FLX, ECO, 3 | Hexagon hosts the *MSC Nastran 2021 Reference Guide* PDF [unverified: too large to open]. Oracles: pyNastran (BSD-3), meshio (MIT) | Build from the vendor reference guide; read OP2 from sample files and pyNastran's behaviour |
| **Abaqus .inp** | FE model exchange | FLX, ECO, 3 | Keywords Reference in Abaqus documentation [unverified: access not checked]. meshio reads `.inp` | Build from the keyword documentation; oracle meshio |
| **COMSOL .mph** | Model exchange | FLX, 4+ | No public specification found [unverified] | Do not build. Use COMSOL's exports to open formats, run by the customer |
| **Mastercam posts (.pst / MP language)** | Matching the G-code that shops already accept | MFG, 2 | The MP Post Processor Reference Guide is sold through resellers (per an eMastercam forum notice). No open specification found | Do not read posts. Reproduce the *output dialect* per controller from posted samples the reference shop provides (D-MFG-5 already qualifies posts this way) |

## 4. Behaviour to study

These are behaviours to reproduce from vendor documentation, published benchmarks and black-box use of licensed copies. Nothing here involves reading code. Every product is proprietary, linked by nothing, and named internally only (ANV keeps commercial-kernel comparisons internal).

| Incumbent behaviour | What Crucible would reproduce | Tab, phase | Source to study |
| --- | --- | --- | --- |
| Onshape FeatureScript and Part Studio regeneration; microversions; Compare | Feature language, query semantics, history and merge, geometry diff | ING, KLN, UIX, 1 to 2 | FeatureScript docs; Onshape Compare (cited in ING, KLN, UIX) |
| Siemens D-Cubed 2D and 3D DCM; synchronous technology | Sketch and assembly solving, constraint diagnosis, direct edits | MEC, 1 to 2 | Vendor documentation; SketchGraphs replay (MEC) |
| Parasolid and ACIS blends as seen in Plasticity; Alias, ICEM and xNURBS surface analysis | Fillet robustness, G2 and G3 surfacing, zebra and highlight lines | ANV, MEC, 1 to 2 | Re-fillet benchmark corpus; vendor feature docs |
| SOLIDWORKS, NX, CATIA and Creo on NIST MBE PMI test cases | AP242 semantic PMI completeness | MEC, ECO, 1 to 2 | NIST CTC, FTC, STC and HTC cases; CAx-IF round results |
| Mastercam Dynamic Motion, Fusion Adaptive, hyperMILL, NX CAM | Constant-engagement roughing at the measured bound (D-MFG-7 is already clean-room) | MFG, 2 | Published cycle times; reference-shop trials. Counsel first on US 9,164,503 |
| VERICUT, ModuleWorks | NC verification and material removal | MFG, 2 | Vendor docs; posted-code corpora |
| Ansys, Abaqus, COMSOL, LS-DYNA, Moldflow, MAGMASOFT, AutoForm, SYSWELD | Analysis coverage and benchmark parity | FLX, COV, MFG, 2 to 7 | NAFEMS benchmarks, verification manuals, published challenge results (COV rows) |
| Altium, Allegro, Xpedition; KiCad push and shove | Interactive routing, DRC speed, delay tuning | ELX, UIX, 3 | Vendor documentation; replayed sessions |
| Sigrity, HyperLynx, Polar Si9000 | SI and PI analysis results | ELX, 3 | Coupon measurements; IEEE 802.3ck channels |
| Teamcenter and Windchill change workflows; product configurator | ECR, ECO and ECN, effectivity, 150% BOM | KLN, 3 | Vendor documentation (KLN) |
| Zoo Zookeeper, Fusion Assistant and MCP, NX Copilot | Agent behaviour in CAD | AGT, UIX, 1 to 2 | Public demos and documentation (AGT) |
| AI-built clones (SolidCraft, CADCraft) | Speed of feature coverage and MCP ergonomics, the round-4 parity bar | AGT, MEC, 1 | Their repositories (open source, permissive) |

## 5. Using REA safely

### What REA is

REA ("Reverse Engineer Anything", github.com/morluto/rea) is an MCP server and CLI that lets agents inspect native binaries, Electron and JavaScript apps, .NET assemblies, Android packages, Wasm and firmware. Native analysis drives an existing Hopper, Ghidra or IDA installation. The code REA authors is MIT ("REA-authored code is licensed under MIT"); third-party material keeps its own licences.

The README limits its own use to "lawful research, education, interoperability, software preservation, and analysis of software you own or are authorized to examine". It also says it "grants no tool license, key, or activation entitlement". REA is a tool, not a permission: every limit below still applies. It was not run for this digest.

### Legal limits (verified on primary sources unless marked)

- **EU, decompilation.** Directive 2009/24/EC, Article 6, permits reproducing and translating code without authorization only when all of these hold:
  - the person has a right to use the copy;
  - the interoperability information was not "readily available";
  - the acts are confined to the parts needed for interoperability.

  Article 6(2) limits the result. The information may be used only for interoperability of the independently created program, may be given to others only when that is necessary, and may never be used to make a "substantially similar" program or for any other infringing act. Article 6(3) adds the Berne three-step limit.
- **EU, study and contracts.** Article 5(3) lets a lawful user "observe, study or test the functioning of the program in order to determine the ideas and principles" while running it normally. Article 8, second paragraph: "Any contractual provisions contrary to Article 6 or to the exceptions provided for in Article 5(2) and (3) shall be null and void." In the EU, therefore, a EULA cannot remove these rights.
- **EU, file formats.** CJEU C-406/10, *SAS Institute v World Programming* (Grand Chamber, 2 May 2012), held that a program's functionality, programming language and data file formats are not forms of expression protected by copyright. The WIPO Lex record was opened; the judgment text did not render, so the operative wording comes from secondary reports [unverified].
- **US, anti-circumvention.** 17 U.S.C. 1201(f)(1) to (4) allows circumventing a technological protection measure, and sharing what is learned, "for the sole purpose" of interoperability of an independently created program. It covers only section 1201 liability. Each paragraph keeps the condition that the acts "do not constitute infringement", and (f)(3) adds "or violate applicable law other than this section", so contract law still applies.
- **US, copyright.** *Sega v. Accolade*, 977 F.2d 1510 (9th Cir. 1992), held that disassembly is fair use "as a matter of law" when it is the only way to reach unprotected functional elements and there is a legitimate reason.
- **US, contracts override this.** *Bowers v. Baystate*, 320 F.3d 1317 (Fed. Cir. 2003, applying First Circuit law), enforced a shrink-wrap clause prohibiting reverse engineering. It held that the Copyright Act does not "preempt or narrow the scope" of the contract claim; Judge Dyk dissented on preemption. In the US, then, a EULA's anti-reverse-engineering clause can make decompilation a breach of contract even where fair use would protect it.
- **Trade secrets.** The EU Trade Secrets Directive 2016/943, Article 3(1)(b), makes reverse engineering of a lawfully held product a lawful acquisition only if the person is "free from any legally valid duty to limit the acquisition". The US Defend Trade Secrets Act, 18 U.S.C. 1839(6)(B), says improper means "does not include reverse engineering, independent derivation, or any other lawful means of acquisition".
- **Patents.** Clean-room work does not avoid patents. 35 U.S.C. 271(a) makes "whoever without authority makes, uses, offers to sell, or sells any patented invention" an infringer, and the statute has no independent-creation defence. European national laws likewise have no independent-creation defence, only prior-use rights [unverified: not opened]. Every clean-room reader still goes through counsel's freedom-to-operate search, as the phase 0 gate already requires for chains A and B.
- **Trademarks.** Readers are named by the format ("reads DWG"), never with vendor logos, and carry a non-affiliation line, as CADCraft and the ODA specification both do.

What follows for Crucible:

- In the EU, decompilation for file-format interoperability is lawful within Article 6, and no EULA can remove it.
- In the US, it depends on the licence of the copy being examined. Where the EULA forbids reverse engineering, only black-box observation (5(3)-style study, and analysis of files the software writes) is safe.
- Everywhere, decompilation comes after published specifications, open readers and sample-file analysis, because Article 6(1)(b) requires the information not to be "readily available". That excludes DWG (the ODA specification exists), JT (ISO), Eagle (XML) and Nastran (vendor reference).
- **[unverified]** Which jurisdiction governs a given Crucible agent run, and whether Crucible's owning entity sits in the EU, decides which rule applies. Counsel answers this before any decompilation.

### Proposed clean-room protocol (fits contract 13.2)

Precedent: SolidCraft's CLAUDE.md already runs a lighter version. Incumbent observations stay in a gitignored `plan/fusion/`; command ids are kept "as identifiers only"; GPL CAD sources are never read; ATTRIBUTION.md records provenance. It has no separation of roles. The protocol below adds that separation and decompilation limits.

1. **Two new agent roles beside the oracle, builder and verifier roles.**
   - The **observer** may run REA, and only on software the founder holds a licence to examine.
   - Before each engagement, the observer records the copy's licence and its reverse-engineering clause, the jurisdiction, and counsel's clearance.
   - It works in an isolated, egress-denied workspace outside the repository. It writes only a behavioural specification of the format or protocol (record layouts, field meanings, invariants, version differences) and test vectors: sample files the founder's licensed copy produced from Crucible-authored inputs, with expected values.
   - The observer never writes code, pseudocode, decompiled identifiers or control flow into the specification.
   - The **implementer** is a builder that never has REA, the observer's workspace or any decompiled output. It works only from the specification, the vectors and public documents.
2. **A gate between the two roles.** The verifier role reads each specification before release and rejects anything that copies expression: decompiled names, code structure, comments, or algorithm descriptions beyond the format's data semantics.
   - Released specifications and vectors enter `oracles/` through a Proposal, the existing path for corpora (13.2).
   - Each carries a signed provenance record: observer run id, method (published document, file analysis, black-box run, or decompilation, with the exact parts touched), tool and target versions, licence reference and counsel clearance id.
   - Builders' Proposals cite the specification ids they used.
3. **Scope limits.**
   - Order of methods: published specifications, then open readers, then analysis of sample files, then black-box observation of the running program. Decompilation comes only when all of those fail, and only of the parsing and serialization parts needed for the format or protocol (Article 6(1)(c)).
   - Never decompile an incumbent's geometry kernel, solver, mesher, CAM strategy or other algorithm. Never decompile to make a substantially similar program.
   - Never circumvent licence checks or activation; REA's own terms exclude that.
   - Never commit vendor binaries, outputs from vendor sample files, artwork or text.
   - Every resulting reader passes counsel's freedom-to-operate check before release.

### Next steps

- File a change request against ECO, replacing "Crucible never reverse-engineers a proprietary format". It would permit clean-room readers under this protocol, with contract 7.7 and 13.2 naming the observer role.
- Ask counsel, as part of the outside inputs already planned for phase 0, for the jurisdiction answer and a template engagement clearance.
- Take DWG first. It needs no decompilation at all: the ODA specification plus ACadSharp and LibreDWG as oracles, or acadrust after an audit.

## Sources

Every page below was opened on 12 October 2026 unless marked otherwise.

Projects:

- truck: https://github.com/ricosjp/truck
- Fornjot: https://github.com/hannobraun/fornjot
- SolidCraft: https://github.com/bherbruck/solvecraft
- SolidCraft's CLAUDE.md: https://raw.githubusercontent.com/bherbruck/solvecraft/main/CLAUDE.md
- storytold: https://github.com/storytold
- CADCraft: https://github.com/storytold/cadcraft and https://raw.githubusercontent.com/storytold/cadcraft/main/README.md
- acadrust: https://docs.rs/crate/acadrust/latest
- ACadSharp: https://github.com/DomCR/ACadSharp
- LibreDWG: https://github.com/LibreDWG/libredwg
- ODA DWG specification v5.4.1: https://www.opendesign.com/files/guestdownloads/OpenDesign_Specification_for_.dwg_files.pdf
- faer: https://github.com/sarah-quinones/faer-rs
- MFEM: https://github.com/mfem/mfem
- libCEED: https://github.com/CEED/libCEED
- PETSc: https://petsc.org/release/install/license/
- hypre: https://github.com/hypre-space/hypre
- deal.II: https://raw.githubusercontent.com/dealii/dealii/master/LICENSE.md
- SUNDIALS: https://github.com/LLNL/sundials
- SLEPc: https://github.com/slepc/slepc
- bempp-rs: https://github.com/bempp/bempp-rs
- Clarabel.rs: https://github.com/oxfordcontrol/Clarabel.rs
- Palace: https://github.com/awslabs/palace
- PyBaMM: https://github.com/pybamm-team/PyBaMM
- Cantera: https://raw.githubusercontent.com/Cantera/cantera/main/License.txt
- Project Chrono: https://github.com/projectchrono/chrono
- IPC Toolkit: https://github.com/ipc-sim/ipc-toolkit
- FEBio: https://github.com/febiosoftware/FEBio
- Capytaine: https://github.com/capytaine/capytaine
- PyFR: https://github.com/PyFR/PyFR
- Axom: https://github.com/LLNL/axom
- Algoim: https://raw.githubusercontent.com/algoim/algoim/master/LICENSE
- Geogram: https://github.com/BrunoLevy/geogram
- robust: https://github.com/georust/robust
- Manifold: https://github.com/elalish/manifold
- spade: https://github.com/Stoeoef/spade
- iOverlay: https://github.com/iShape-Rust/iOverlay
- cavalier_contours: https://github.com/jbuckmccready/cavalier_contours
- meshoptimizer: https://github.com/zeux/meshoptimizer
- OpenSubdiv: https://raw.githubusercontent.com/PixarAnimationStudios/OpenSubdiv/release/LICENSE.txt
- OpenUSD: https://raw.githubusercontent.com/PixarAnimationStudios/OpenUSD/dev/LICENSE.txt
- fTetWild: https://github.com/wildmeshing/fTetWild
- Fidget: https://github.com/mkeeter/fidget
- libfive: https://github.com/libfive/libfive
- parry: https://github.com/dimforge/parry
- nalgebra: https://github.com/dimforge/nalgebra
- wgpu: https://github.com/gfx-rs/wgpu
- egui: https://github.com/emilk/egui
- Parley: https://github.com/linebender/parley
- HarfRust: https://github.com/harfbuzz/harfrust
- fontations: https://github.com/googlefonts/fontations
- Taffy: https://github.com/DioxusLabs/taffy
- AccessKit: https://github.com/AccessKit/accesskit
- winit: https://github.com/rust-windowing/winit
- Wasmtime: https://raw.githubusercontent.com/bytecodealliance/wasmtime/main/LICENSE
- Loro: https://github.com/loro-dev/loro
- Cedar: https://github.com/cedar-policy/cedar
- Salsa: https://github.com/salsa-rs/salsa
- rowan: https://github.com/rust-analyzer/rowan
- pubgrub: https://github.com/pubgrub-rs/pubgrub
- CORE-MATH: https://core-math.gitlabpages.inria.fr/
- lib3mf: https://github.com/3MFConsortium/lib3mf
- ngspice: https://sourceforge.net/p/ngspice/ngspice/ci/master/tree/COPYING
- sparrow: https://github.com/JeroenGar/sparrow
- jagua-rs: https://github.com/JeroenGar/jagua-rs
- Renode: https://github.com/renode/renode
- pyNastran: https://raw.githubusercontent.com/SteveDoyle2/pyNastran/main/LICENSE.md
- meshio: https://github.com/nschloe/meshio
- Foxtrot: https://github.com/Formlabs/foxtrot
- ruststep: https://github.com/ricosjp/ruststep
- Zoo modeling app: https://github.com/KittyCAD/modeling-app
- Open CASCADE: https://occt3d.com/open-cascade-technology/index.html
- FreeCAD: https://github.com/FreeCAD/FreeCAD
- KiCad licences: https://www.kicad.org/about/licenses/ and https://www.kicad.org/libraries/license/
- KiCad source: https://github.com/KiCad/kicad-source-mirror
- KiCad import formats: https://dev-docs.kicad.org/en/import-formats/
- KiCad 10 importers: https://www.kicad.org/blog/2026/02/Three-New-Importers-in-KiCad-10-Allegro-PADS-and-gEDA/
- CalculiX: http://www.dhondt.de/
- Elmer: https://github.com/ElmerCSC/elmerfem/blob/devel/LICENSE.md
- OpenFOAM: https://openfoam.org/licence/
- Gmsh: https://gmsh.info/
- PrusaSlicer: https://github.com/prusa3d/PrusaSlicer
- OrcaSlicer: https://github.com/SoftFever/OrcaSlicer
- OpenCAMLib: https://github.com/aewallin/opencamlib
- Freerouting: https://github.com/freerouting/freerouting
- OpenVAF: https://github.com/pascalkuthe/OpenVAF
- VACASK: https://codeberg.org/arpadbuermen/VACASK
- REA: https://github.com/morluto/rea

Law:

- Directive 2009/24/EC, Articles 5, 6 and 8 (legislation.gov.uk's copy of the EU text): https://www.legislation.gov.uk/eudr/2009/24/article/5, https://www.legislation.gov.uk/eudr/2009/24/article/6 and https://www.legislation.gov.uk/eudr/2009/24/article/8
- Directive (EU) 2016/943, Article 3: https://www.legislation.gov.uk/eudr/2016/943/article/3
- 17 U.S.C. 1201: https://www.law.cornell.edu/uscode/text/17/1201
- 18 U.S.C. 1839: https://www.law.cornell.edu/uscode/text/18/1839
- 35 U.S.C. 271: https://www.law.cornell.edu/uscode/text/35/271
- *Bowers v. Baystate*, 320 F.3d 1317: https://law.resource.org/pub/us/case/reporter/F3/320/320.F3d.1317.01-1109.01-1108.html and https://caselaw.findlaw.com/court/us-federal-circuit/1202776.html
- *Sega v. Accolade*, 977 F.2d 1510: https://law.resource.org/pub/us/case/reporter/F2/977/977.F2d.1510.92-15655.html
- C-406/10 *SAS Institute v World Programming* (WIPO Lex record only; the judgment text did not render): https://www.wipo.int/wipolex/en/judgments/details/1728

Not opened, so the claims resting on them are marked [unverified] above:

- Siemens' Parasolid documentation
- SOLIDWORKS Document Manager help (the page did not render)
- Autodesk RealDWG (403)
- MSC Nastran 2021 Reference Guide (too large to open)
- the Abaqus documentation
- the EUR-Lex and CURIA texts (they did not render)
