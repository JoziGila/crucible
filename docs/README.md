# Crucible spec

Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from a single typed model. This folder is its specification: a binding architecture contract, twelve subsystem specs, an adversarial review and the revision work in progress. Crucible, Ingot, Anvil, Flux and Kiln are working names.

The published view is the Claude Doc [Crucible — Platform Spec](https://claude.ai/code/artifact/bb8a8fb2-1060-40c5-98b7-fe5ef6148a0c). This folder is the source of truth; the doc is published from it.

## Reading order

1. [`spec/00-overview.md`](spec/00-overview.md): the platform on one page, summarizing the contract and every tab.
2. [`contract.md`](contract.md): names, principles, core types, decided architecture, roadmap, program plan and performance targets. Binding on every tab.
3. [`spec/`](spec/): one file per subsystem.

| # | Subsystem | Code | Owns |
| --- | --- | --- | --- |
| 01 | [Ingot language](spec/01-ingot.md) | ING | The design language |
| 02 | [Anvil geometry kernel](spec/02-anvil.md) | ANV | Geometry in every representation |
| 03 | [Flux physics engine](spec/03-flux.md) | FLX | The simulation engine |
| 04 | [Physics coverage and materials](spec/04-coverage.md) | COV | Which physics and scales are covered, and with what validity |
| 05 | [Kiln, repository and PLM](spec/05-kiln-repo-plm.md) | KLN | Incremental evaluation, versioning and product lifecycle |
| 06 | [Mechanical design](spec/06-mechanical.md) | MEC | Everything a mechanical designer does |
| 07 | [Manufacturing](spec/07-manufacturing.md) | MFG | Turning designs into physical parts |
| 08 | [Electronics and systems](spec/08-electronics-systems.md) | ELX | Boards, mechatronics and system models |
| 09 | [Agents](spec/09-agents.md) | AGT | Agents as first-class users |
| 10 | [UI and interaction](spec/10-ui.md) | UIX | How people see and steer |
| 11 | [Interop and ecosystem](spec/11-interop-ecosystem.md) | ECO | Standards, extensions and the open ecosystem |
| 12 | [Platform and performance](spec/12-platform-performance.md) | PLT | Every operating system, fast and identical |

## Status

Round 2 is closed (tag `round-2`): every tab is revised against contract v5 and the review findings that target it, the tabs agree with each other, and every tab is published in the Claude Doc.

| Tab | Version | Words excluding Sources | Review findings (Critical) | In the doc |
| --- | --- | --- | --- | --- |
| Overview | v2 | 6,600 | n/a | v2 |
| ING | v2 | 19,600 | 47 (6) | v2 |
| ANV | v2 | 20,000 | 61 (8) | v2 |
| FLX | v2 | 17,900 | 66 (7) | v2 |
| COV | v2 | 17,800 | 33 (5) | v2 |
| KLN | v2 | 17,900 | 79 (12) | v2 |
| MEC | v2 | 17,900 | 45 (2) | v2 |
| MFG | v2 | 17,800 | 41 (3) | v2 |
| ELX | v2 | 17,400 | 36 (4) | v2 |
| AGT | v2 | 17,800 | 42 (7) | v2 |
| UIX | v2 | 17,900 | 42 (3) | v2 |
| ECO | v2 | 17,900 | 48 (1) | v2 |
| PLT | v2 | 17,800 | 61 (2) | v2 |
| Adversarial review | v1 | 7,800 | n/a | v1 |
| Decisions log | v1 | 380 decisions | n/a | v1 |

A finding can target several tabs, so the column sums to more than the 295 findings.

## Layout

```
contract.md              binding architecture contract (v5)
spec/                    the doc's tabs, one file each; diagrams/ holds widget sources
review/                  six adversarial reviews, their brief and findings.json
revision/                round 2 brief, one findings packet per tab, publishing notes, work in progress
tools/                   check.py (spec check), extract.py (cross-tab extracts), findings.py
```

## History

| Tag | What it marks |
| --- | --- |
| `round-1` | First drafts of the twelve subsystem tabs under contract v3 |
| `review` | Six adversarial reviews: 295 findings, 23 of them Critical |
| `contract-v4` | Contract v4 with the review rulings, the round 2 brief and the revision packets |
| `round-2` | Contract v5, all twelve tabs revised and consistent, the overview, the adversarial review and the decisions log, all published |

`git show round-1:docs/spec/<file>.md` prints a tab's first draft.

## Tools

```
python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-1   # contract rules, skeleton, oracles, decisions, cuts
python3 docs/tools/check.py --all -q                                      # every tab
python3 docs/tools/extract.py                                             # decisions, change requests, interfaces, open questions
python3 docs/tools/findings.py                                            # re-parse docs/review/ into docs/review/findings.json
```

Run them from the repository root. Python 3.9 or later, standard library only.
