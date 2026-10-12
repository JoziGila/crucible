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

Round 4 is closed (tag `round-4`). Contract v7.4 is binding. Every subsystem tab is v4: revised against all three adversarial reviews, held to the parity floor of contract 13.4, consistent with the other tabs, written teach-first for a human reader, and published in the Claude Doc. Phase 0 starts next in this repository. A few open questions remain in the tabs, each waiting on an outside input such as counsel's opinions.

| Tab | Version | Words of prose | Findings (Critical): first · second · third review | In the doc |
| --- | --- | --- | --- | --- |
| Overview | v4 | 6,646 | n/a | v4 |
| ING | v4 | 14,339 | 47 (6) · 47 (5) · 42 (5) | v4 |
| ANV | v4 | 15,770 | 61 (8) · 55 (4) · 63 (6) | v4 |
| FLX | v4 | 14,653 | 66 (7) · 58 (4) · 82 (7) | v4 |
| COV | v4 | 11,902 | 33 (5) · 37 (1) · 53 (5) | v4 |
| KLN | v4 | 14,597 | 79 (12) · 96 (6) · 99 (11) | v4 |
| MEC | v4 | 13,896 | 45 (2) · 64 (2) · 80 (5) | v4 |
| MFG | v4 | 12,247 | 41 (3) · 56 (3) · 46 (3) | v4 |
| ELX | v4 | 12,926 | 36 (4) · 23 (1) · 35 (0) | v4 |
| AGT | v4 | 12,816 | 42 (7) · 56 (7) · 53 (5) | v4 |
| UIX | v4 | 14,301 | 42 (3) · 32 (1) · 54 (6) | v4 |
| ECO | v4 | 13,105 | 48 (1) · 51 (2) · 40 (0) | v4 |
| PLT | v4 | 13,675 | 61 (2) · 58 (3) · 51 (6) | v4 |
| Adversarial review | v3 | 16,700 with tables | n/a | v3 |
| Decisions log | v3 | 506 decisions | n/a | v3 |

Words of prose exclude tables, Reference and Sources (contract 11). A finding can target several tabs, so the columns sum to more than the 295, 278 and 312 findings.

## Layout

```
contract.md              binding architecture contract (v7.4)
spec/                    the doc's tabs, one file each; diagrams/ holds widget sources
review/                  twenty-one adversarial reviews (rounds of six, six and nine), the current brief and findings.json
revision/                revision brief, one findings packet per tab, consistency brief, software digest, publishing notes
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
| `third-review` | Third adversarial review of the v3 spec by nine reviewers, including competitive parity and human readability: 312 findings, 18 of them Critical |
| `round-4` | Contract v7.4 (agents author and people view, parity floor, clean-room insight protocol, Git-native history), all twelve tabs at v4 and consistent, the summary tabs rewritten, all published |

`git show round-1:docs/spec/<file>.md` prints a tab's first draft.

## Tools

```
python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-3   # contract rules, skeleton, oracles, decisions, cuts
python3 docs/tools/check.py --all -q                                      # every tab
python3 docs/tools/extract.py                                             # decisions, change requests, interfaces, open questions
python3 docs/tools/findings.py                                            # re-parse docs/review/ into docs/review/findings.json
```

Run them from the repository root. Python 3.9 or later, standard library only.
