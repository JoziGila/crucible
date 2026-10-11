# Crucible: working notes for Claude Code

Crucible is a Rust platform where people and agents design, simulate, manufacture and release physical products from one typed model. We specify it in full detail first, in `docs/`, and then build it in this repository from that spec. `docs/README.md` has the reading order and the status table.

The spec work is in round 2: each subsystem tab is revised against the binding contract and an adversarial review, then the contract, the summary tabs and the published doc are brought into agreement.

## Rules that always apply

- `docs/` holds the whole spec: contract, tabs, reviews, revision work and the spec tools. The repository root is kept for the build.
- `docs/contract.md` is binding; a tab that disagrees with it is wrong. Never edit the contract while revising a tab: file a request under that tab's "Contract change requests". The contract changes only in a ruling step, which edits it, adds a row to its newest ruling log and bumps the version in its title and lead.
- Names follow contract section 2, including the "Never call it" column. Fidelity names are only `Preview`, `Interactive` and `SignOff`.
- Every tab follows contract sections 10 and 11: the skeleton, one capability table at the end of each design section, inline decisions with stable numbers, 12,000 to 18,000 words excluding Sources (ING and ANV up to 20,000), and a calm present-tense voice.
- Each fact lives in the tab that owns it. Other tabs state the consequence in one line and point to the owner.
- Research: cite only pages you opened, mark unverified claims [unverified], and never invent version numbers, dates, statistics or customer names.
- After editing a tab, `python3 docs/tools/check.py docs/spec/<file>.md --base round-1` must report zero errors before the commit.
- The Claude Doc is a published view of committed text (`docs/revision/publish.md`). `docs/build/` is scratch and ignored by git.

## Where things stand (2026-10-11)

- Contract v4.1: rulings on round 1 (section 14), the review (15) and the first revised tabs (16). CCR-FLX-9, one shared phase table, is open.
- ANV v2 is done and published. FLX v2 is done and passes the check, but is not published.
- ING is v1, with a partial v2 in `docs/revision/wip/01-ingot.partial.md` (lead, scope and the start of lexical syntax).
- COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO and PLT are v1. Each has its packet in `docs/revision/packets/`.
- The Overview is the pre-review text. The Adversarial review and Decisions log tabs are not written.

## Plan for the rest of round 2

1. **Shared phase table (CCR-FLX-9).** Do this before revising more tabs, so each cites one table. Read CCR-FLX-9 in `docs/spec/03-flux.md`, finding R1-35 in `docs/review/R1-physics.md` and the Phasing sections of FLX, COV, MEC, MFG and ELX. Add contract 13.4, one row per capability that several tabs phase (modal analysis, inherent strain, DFN batteries, fibre orientation, fill tracking, high-pressure die casting, stability lobes, fitted tetrahedra and the like) with its phase and owner. Log the ruling in section 16 and bump to v4.2.
2. **Revise the ten remaining tabs:** ING, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO and PLT. Run one subagent per tab on `docs/revision/brief.md` (see below). After each report, run the check, read the lead and one section, commit, and update the tab's row in `docs/README.md`.
3. **Rule on the new change requests.** `python3 docs/tools/extract.py` gathers every tab's requests into `docs/build/extracts/ccr.md`. Accept, revise or decline each in contract section 16 and bump to v5.
4. **Consistency pass.** Update citations of accepted requests (ANV still cites CCR-ANV-7 and CCR-ANV-8; FLX cites CCR-FLX-8). Make each row of "Interfaces with other subsystems" match the other tab's row (`docs/build/extracts/interfaces.md`), each phase match contract section 13, and each name match the glossary. Finish with `python3 tools/check.py --all -q` clean.
5. **Adversarial review tab**, `docs/spec/13-adversarial-review.md`: the six reviews, each Critical finding and how it was resolved (contract ruling or tab change), the declined findings with reasons, and what the review changed overall. Draw on `docs/review/`, the packets, contract sections 14 to 16 and each tab's Open questions.
6. **Decisions log**, `docs/spec/14-decisions-log.md`: every decision, grouped by tab, one line each with its reason, marked where revised in round 2 (`docs/build/extracts/decisions.md`).
7. **Overview update.** Bring `docs/spec/00-overview.md` to the contract: the canonical example (6), principles (3), layering (4), per-region Flux discretization (7.1), the roadmap with phases 0 to 7 and GP1 to GP16 (13.1), the program plan (13.2), scope, risks, patents, and the Flux rename as an open question. Redraw both diagrams in `docs/spec/diagrams/`.
8. **Close the round.** All checks clean, the status table in `docs/README.md` current, every tab published, then tag `round-2`.

## Running revisions with subagents

- Brief each agent in one line: "Revise the <tab name> tab (<TAB>, `docs/spec/<file>.md`) following `docs/revision/brief.md`; your packet is `docs/revision/packets/<TAB>.md`; reply with the report the brief asks for."
- Launch every agent of a wave in one message so they run in parallel; use waves of about five if the session limits parallel agents.
- Never send new work to a finished agent as a follow-up message. In this project that ran agents one after another and stalled the session for hours. Start a fresh agent instead.
- Agents write only their own `docs/spec/<file>.md` and `docs/build/<tab>/`. Only the orchestrating session commits and edits `docs/contract.md`, the READMEs and this file.
- Long files are written in parts of at most about 4,000 words and then assembled.
- Web search quota can run out; WebFetch known primary sources instead.

## Commands

```
python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-1   # one tab, plus anything cut since round 1
python3 docs/tools/check.py --all -q                                      # every tab, errors only
python3 docs/tools/extract.py                                             # docs/build/extracts: decisions, requests, interfaces, open questions
git show round-1:docs/spec/06-mechanical.md                               # a tab's first draft
git diff round-1 -- docs/spec/02-anvil.md                                 # what round 2 changed in a tab
```

## Commits

- One commit per tab revision: `<TAB> v2: revise against contract v4.x and <n> review findings`. The body lists declined findings with reasons, decisions added and revised, and the word count.
- Contract commits: `Contract v<x>: <what was ruled>`.
- There is no remote. Do not push unless asked.
