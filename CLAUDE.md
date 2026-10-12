# Crucible: working notes for Claude Code

Crucible is a Rust platform where people and agents design, simulate, manufacture and release physical products from one typed model. We specify it in full detail first, in `docs/`, and then build it in this repository from that spec. `docs/README.md` has the reading order and the status table.

The spec has finished round 4: three adversarial reviews, each followed by a revision of every tab, a contract ruling and a consistency pass. Phase 0 (the build) starts next in this repository.

## Rules that always apply

- `docs/` holds the whole spec: contract, tabs, reviews, revision work and the spec tools. The repository root is kept for the build.
- `docs/contract.md` is binding; a tab that disagrees with it is wrong. Never edit the contract while revising a tab: file a request under that tab's "Contract change requests". The contract changes only in a ruling step, which edits it, adds a row to its newest ruling log and bumps the version in its title and lead.
- Names follow contract section 2, including the "Never call it" column. Fidelity names are only `Preview`, `Interactive` and `SignOff`.
- Every tab follows contract sections 10 and 11: the skeleton, one capability table at the end of each design section, inline decisions with stable numbers, 9,000 to 15,000 words of prose with tables, Reference and Sources excluded (ING and ANV up to 17,000), and a calm present-tense voice.
- Each fact lives in the tab that owns it. Other tabs state the consequence in one line and point to the owner.
- Research: cite only pages you opened, mark unverified claims [unverified], and never invent version numbers, dates, statistics or customer names.
- After editing a tab, `python3 docs/tools/check.py docs/spec/<file>.md --base round-3` must report zero errors before the commit.
- The Claude Doc is a published view of committed text (`docs/revision/publish.md`). `docs/build/` is scratch and ignored by git.

## Where things stand (2026-10-12)

- Round 4 is closed (tag `round-4`). Contract v7.4 is binding: rulings on round 1 (section 14), the first review (15), round 2 (16), the second review and round 3 (17), and the third review, the founder's directions and round 4's change requests (18), with one shared phase table and parity floor (13.4).
- Founder directions in force: agents author and people steer, review and present, so the UI is a viewer and presentation studio first (polish reference: Anatomy, github.com/wheresryan22/anatomy); reverse engineering is for insight only under the clean-room protocol (7.7); history is Git-native, any Git host can be home and Kiln guards protected branches as a required check and at release (7.1).
- Crucible is built by agents with one founder (contract 13.2): no staffing, hires, engineer-years or calendar months anywhere in the spec.
- All twelve subsystem tabs are v4, consistent, and pass the check; the Overview, Adversarial review and Decisions log are current; every tab is published in the Claude Doc.
- A few open questions remain in the tabs, each waiting on an outside input (counsel's opinions, partner agreements).
- The repository is public at github.com/JoziGila/crucible (`origin`). Commit with the personal identity already configured.

## Next: phase 0

Phase 0 builds the foundations that contract 13.1's phase 0 gate names (determinism suite, units, kernel IR v0, interface-first oracle crates) by the agent roles of 13.2: the oracle role writes contract crates and oracles first, builders implement, the verifier attacks. Outside inputs (counsel, name clearance, ISO's answer on STEP schemas, GP2's print bureau) proceed in parallel. A spec change after round 4 goes through a contract change request and a ruling, never a silent edit.

## Running revisions with subagents

- Brief each agent in one line: "Revise the <tab name> tab (<TAB>, `docs/spec/<file>.md`) following `docs/revision/brief.md`; your packet is `docs/revision/packets/<TAB>.md`; reply with the report the brief asks for."
- Launch every agent of a wave in one message so they run in parallel; use waves of about five if the session limits parallel agents.
- Never send new work to a finished agent as a follow-up message. In this project that ran agents one after another and stalled the session for hours. Start a fresh agent instead.
- Agents write only their own `docs/spec/<file>.md` and `docs/build/<tab>/`. Only the orchestrating session commits and edits `docs/contract.md`, the READMEs and this file.
- Long files are written in parts of at most about 4,000 words and then assembled.
- Web search quota can run out; WebFetch known primary sources instead.

## Commands

```
python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-3   # one tab, plus anything cut since round 3
python3 docs/tools/check.py --all -q                                      # every tab, errors only
python3 docs/tools/extract.py                                             # docs/build/extracts: decisions, requests, requires, glossary, open questions
git show round-1:docs/spec/06-mechanical.md                               # a tab's first draft
git diff round-1 -- docs/spec/02-anvil.md                                 # what round 2 changed in a tab
```

## Commits

- One commit per tab revision: `<TAB> v<n>: revise against contract v<x> and <n> review findings`. The body lists declined findings with reasons, decisions added and revised, and the word count.
- Contract commits: `Contract v<x>: <what was ruled>`.
- Push each commit to `origin` after the check passes. Never rewrite published history.
