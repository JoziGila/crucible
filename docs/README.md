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

Round 3 is closed (tag `round-3`). Contract v6.1 is binding. Every subsystem tab is v3: revised against both adversarial reviews, consistent with the other tabs, with every `[unverified]` claim checked or cut, and published in the Claude Doc. About a dozen open questions remain, each waiting on an outside input such as counsel's opinion, the first calibration build or later-phase data.

| Tab | Version | Words excluding Sources | Findings (Critical): first review · second review | In the doc |
| --- | --- | --- | --- | --- |
| Overview | v3 | 7,000 | n/a | v3 |
| ING | v3 | 19,900 | 47 (6) · 47 (5) | v3 |
| ANV | v3 | 19,900 | 61 (8) · 55 (4) | v3 |
| FLX | v3 | 18,000 | 66 (7) · 58 (4) | v3 |
| COV | v3 | 17,700 | 33 (5) · 37 (1) | v3 |
| KLN | v3 | 18,000 | 79 (12) · 96 (6) | v3 |
| MEC | v3 | 18,000 | 45 (2) · 64 (2) | v3 |
| MFG | v3 | 17,900 | 41 (3) · 56 (3) | v3 |
| ELX | v3 | 18,000 | 36 (4) · 23 (1) | v3 |
| AGT | v3 | 17,900 | 42 (7) · 56 (7) | v3 |
| UIX | v3 | 17,900 | 42 (3) · 32 (1) | v3 |
| ECO | v3 | 17,700 | 48 (1) · 51 (2) | v3 |
| PLT | v3 | 17,800 | 61 (2) · 58 (3) | v3 |
| Adversarial review | v2 | 10,700 | n/a | v2 |
| Decisions log | v2 | 441 decisions | n/a | v2 |

A finding can target several tabs, so the columns sum to more than the 295 and 278 findings.

## Layout

```
contract.md              binding architecture contract (v7)
spec/                    the doc's tabs, one file each; diagrams/ holds widget sources
review/                  twelve adversarial reviews (two rounds of six), the current brief and findings.json
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
| `second-review` | Second adversarial review of the v2 spec: 278 findings, 16 of them Critical |
| `round-3` | Contract v6.1 with an agent-built program, all twelve tabs at v3 and consistent, every claim verified or cut, the summary tabs updated, all published |

`git show round-1:docs/spec/<file>.md` prints a tab's first draft.

## Tools

```
python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-1   # contract rules, skeleton, oracles, decisions, cuts
python3 docs/tools/check.py --all -q                                      # every tab
python3 docs/tools/extract.py                                             # decisions, change requests, interfaces, open questions
python3 docs/tools/findings.py                                            # re-parse docs/review/ into docs/review/findings.json
```

Run them from the repository root. Python 3.9 or later, standard library only.
