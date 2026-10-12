<p align="center"><sub><i>
One Rust platform to rule them all,<br>
One Rust platform to find them,<br>
One Rust platform to bring them all<br>
And in the darkness bind them.
</i></sub></p>

<p align="center">
  <img src=".github/assets/banner.svg" alt="Crucible: design, simulate, make and release physical products from one typed model" width="100%">
</p>

<p align="center">
  <a href="docs/README.md"><img alt="Status: open specification" src="https://img.shields.io/badge/status-spec%20done%2C%20code%20next-4c8dff?style=flat-square"></a>
  <a href="docs/contract.md"><img alt="Contract v7.4" src="https://img.shields.io/badge/contract-v7.4-1f2843?style=flat-square"></a>
  <a href="docs/spec/"><img alt="12 subsystem specs" src="https://img.shields.io/badge/spec-12%20subsystems-1f2843?style=flat-square"></a>
  <a href="docs/review/"><img alt="Three adversarial reviews: 885 findings" src="https://img.shields.io/badge/torn%20apart-3%20times%2C%20885%20findings-1f2843?style=flat-square"></a>
  <a href="LICENSE"><img alt="Code: Apache-2.0 WITH LLVM-exception" src="https://img.shields.io/badge/code-Apache--2.0%20WITH%20LLVM--exception-1f2843?style=flat-square"></a>
  <a href="LICENSE-DOCS"><img alt="Docs: CC BY 4.0" src="https://img.shields.io/badge/docs-CC%20BY%204.0-1f2843?style=flat-square"></a>
</p>

Designing a bracket today takes five apps, three file exports and that one engineer who knows which STEP flavour the machine shop likes. The CAD file doesn't know about the stress check. The stress check doesn't know about the toolpath. The bill of materials lives in a spreadsheet with a login, and nobody remembers why the fillet is 2 mm.

Crucible is my attempt to make all of that one thing. A product is a typed program: the geometry, the physics, the toolpaths, the drawings and the bill of materials are all computed from it, so one edit reaches every one of them in the same breath. It is written in Rust, top to bottom, and it is being built by a swarm of AI agents and me. There is no team. There is a very long spec.

> [!NOTE]
> **Nothing runs yet.** The spec is finished: a binding contract, twelve subsystem specs, and three adversarial reviews by twenty-one reviewers who filed 885 findings and were, frankly, rude about it. Every finding was fixed, ruled on or declined with a reason. The Rust code starts next, in this repository, against that spec.

## What it's for

<p align="center">
  <img src=".github/assets/products.svg" alt="Sixteen golden products, from a MEMS accelerometer to a workboat hull" width="100%">
</p>

Not demo cubes. Each phase of the roadmap ends with a **golden product**: a real thing designed and checked in Crucible, made by a real shop or printer, and measured by a lab that doesn't care about my feelings. The list runs from a MEMS accelerometer and a machined bracket to a drone, an EV battery sub-pack, a timber pavilion, a bone plate, a sewn backpack and a workboat hull.

## Twenty lines to a checked part

Here is the bracket every page of the spec keeps coming back to: aluminium, a stiffening web, a sideways load and one requirement.

```rust
use std::mech::{sketch, rect, extrude, rib, fillet, part}
use std::materials::alu_6061_t6
use std::sim::quick::static_stress

/// L-bracket with a stiffening web.
#[toolbox(category: "Structure", icon: "bracket")]
pub feature bracket(
    #[ui(step: 5mm)]
    width: Length in 20mm..=400mm = 60mm,
    thickness: Length = 6mm ± 0.1mm,
    load: Force = 1.2kN,
) -> Part {
    let outline = rect(width, 40mm)
    let base = sketch(plane.xy) { outline } |> extrude(thickness)
    let web = base.edge(role: end(outline.top)) |> rib(height: 20mm, t: thickness)
    let body = base + web
    let solid = body |> fillet(body.edges(new), 2mm)
    let p = part(solid, name: "Bracket").material(alu_6061_t6)
    let clamp = base.face(role: start_cap)
    let tip = web.face(role: end_cap)
    let study = static_stress(p, fixed: clamp, force: load * dir(-y), on: tip)
    let stress = study.von_mises.max(over: study.regular())
    p.require(stress < 0.6 * p.material.yield_strength(at: 20degC), name: "static_margin")
}
// width + load  →  error ing/3001: cannot add Length and Force
```

<p align="center">
  <img src=".github/assets/bracket-steps.svg" alt="The bracket built in seven steps: sketch, extrude, rib, fillet, part, study, check" width="100%">
</p>

A few things to notice. `width + load` doesn't compile, because adding millimetres to kilonewtons is how bridges fall down. The `#[ui(step: 5mm)]` line gives the viewer a slider, and dragging it rewrites the source, so nothing exists only in a GUI. And the last line is a real check with a name. In the spec's worked numbers the 6 mm plate peaks at 94 MPa against a 144 MPa limit, error bars included, and passes. Make it 4 mm and it fails, and Crucible tells you where and by how much.

Every number Crucible shows carries its error and says how far to trust it. When it can't decide, it says **Undecided** and names the test that would settle it. I'd rather ship that than another confident rainbow plot.

## A Tuesday with Crucible

- **09:00** You ask an agent for a bracket 80 mm wide.
- **09:00:02** It edits one line, the stress check reruns, and the result comes back with its error bar.
- **09:01** A second agent, whose only job is to break the first one's work, attacks it and finds nothing.
- **09:04** You look at it, rotate it, approve it on your phone.
- **Next week** A shop machines it from the exported STEP and drawing, and a lab bends it until the strain gauges agree with the prediction, or don't, in which case we learn something.

Agents do the authoring. People point, mark up, ask, review and present. The interface is a viewer first: fast inspection, photoreal renders, exploded views, simulation you can scrub through, and reports whose numbers are bound to the live model, so a slide can't quietly go stale.

## How it fits together

<p align="center">
  <img src=".github/assets/architecture.svg" alt="Editors, api, Ingot and repo, Kiln, then Anvil, Flux and Wasm components, producing STEP, 3MF, Gerber and signed releases" width="100%">
</p>

| Part | What it does |
| --- | --- |
| **Ingot** | The design language. Pure, strict, statically typed; units and tolerances are types |
| **Anvil** | The geometry kernel: exact B-rep, meshes, implicit shapes and subdivision surfaces |
| **Flux** | The physics engine, where every result comes with an error budget (working name; it gets renamed before anything freezes) |
| **Kiln** | Recomputes only what an edit touched, from a content-addressed cache. History is plain Git: clone it, branch it, open pull requests on GitHub |
| **`api`** | One API for the viewer, agents, the CLI and CI, served over MCP and native SDKs |

A few rules hold everything together. Same inputs give the same bits on Windows, macOS, Linux and in the browser. Built-in features use only the mechanisms anyone else can use. No capability ships without an oracle, a machine-checkable test written before the code, which the agents building that code are not allowed to touch. And anything that leaves Crucible, such as a release, an export or a print job, runs only after a human approves that exact plan. Crucible sends programs to machines. It never presses the green button.

## Roadmap

<p align="center">
  <img src=".github/assets/roadmap.svg" alt="Phases 0 to 7 in order, each closed by golden products GP1 to GP16" width="100%">
</p>

Phases end at gates, not dates. Phase 0 is foundations: determinism, units, the oracles. Phase 1 is the wedge, code-CAD and 3D printing, and it closes when a machined aluminium bracket and a metal-printed lattice bracket have both been made from Crucible's files and load-tested. After that come moulded plastics, a drone, crash structures, castings, and finally boats, buildings, implants and soft goods. Phases 5 to 7 start only once a physical test partner signs on, because simulation without a test rig is just very expensive fan fiction.

## What it won't do

It won't lay out your chip, run nuclear criticality safety, or simulate superconducting magnet quench; it hands those to the specialist tools that already do them well. It won't pretend to predict things nobody can predict yet, like turbulent separation on a smooth body or exactly when a composite cracks. It will flag them and tell you what to test. And it won't be built by reverse engineering anyone's code: we study how the incumbents behave, then build from the papers, cleanly.

## Read the spec

Start with [the Overview](docs/spec/00-overview.md): the whole platform in one sitting. Then [the contract](docs/contract.md), which every subsystem must obey, and then whichever of [the twelve subsystem specs](docs/spec/) you care about. [`docs/README.md`](docs/README.md) has the map and the status of every piece.

## Tell me where it's wrong

The most useful thing you can do right now is find a flaw. Open an issue with the subsystem, the section and what's wrong, plus a source if you have one; the reviews in [`docs/review/`](docs/review/) show the bar. If you think the contract itself is wrong, don't work around it: propose a change request and argue for it. If you edit a spec, run the check first:

```bash
python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-3
```

Sign off your commits under the [Developer Certificate of Origin](https://developercertificate.org/) with `git commit -s`.

## License

Code, including the spec tools, is [Apache-2.0 WITH LLVM-exception](LICENSE). The spec and other docs are [CC BY 4.0](LICENSE-DOCS). Crucible, Ingot, Anvil, Flux and Kiln are working names until the trademark searches come back.
