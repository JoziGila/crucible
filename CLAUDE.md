# Crucible: working notes for Claude Code

Crucible is a Rust platform where people and agents design, simulate, manufacture and release physical products from one typed model. We specify it in full detail first, in `docs/`, and then build it in this repository from that spec. `docs/README.md` has the reading order and the status table.

The spec has finished round 2: every subsystem tab was revised against the binding contract and an adversarial review, then the contract, the tabs, the summary tabs and the published doc were brought into agreement.

## Rules that always apply

- `docs/` holds the whole spec: contract, tabs, reviews, revision work and the spec tools. The repository root is kept for the build.
- `docs/contract.md` is binding; a tab that disagrees with it is wrong. Never edit the contract while revising a tab: file a request under that tab's "Contract change requests". The contract changes only in a ruling step, which edits it, adds a row to its newest ruling log and bumps the version in its title and lead.
- Names follow contract section 2, including the "Never call it" column. Fidelity names are only `Preview`, `Interactive` and `SignOff`.
- Every tab follows contract sections 10 and 11: the skeleton, one capability table at the end of each design section, inline decisions with stable numbers, 12,000 to 18,000 words excluding Sources (ING and ANV up to 20,000), and a calm present-tense voice.
- Each fact lives in the tab that owns it. Other tabs state the consequence in one line and point to the owner.
- Research: cite only pages you opened, mark unverified claims [unverified], and never invent version numbers, dates, statistics or customer names.
- After editing a tab, `python3 docs/tools/check.py docs/spec/<file>.md --base round-3` must report zero errors before the commit.
- The Claude Doc is a published view of committed text (`docs/revision/publish.md`). `docs/build/` is scratch and ignored by git.

## Where things stand (2026-10-11)

- Round 3 is closed (tag `round-3`). Contract v6.1 is binding: rulings on round 1 (section 14), the first review (15), round 2's change requests (16), and the second review and round 3's change requests (17), with one shared phase table (13.4).
- Crucible is built by agents with one founder (contract 13.2): no staffing, hires, engineer-years or calendar months anywhere in the spec.
- All twelve subsystem tabs are v3, consistent with each other, and pass the check; every `[unverified]` claim is checked or cut. The Overview, Adversarial review and Decisions log are current. Every tab is published in the Claude Doc.
- About a dozen open questions remain in the tabs, each waiting on an outside input.
- The repository is public at github.com/JoziGila/crucible (`origin`). Commit with the personal identity already configured.

## Plan for round 4

Decided 2026-10-12: one final review-and-fix pass before phase 0. The spec must have every feature needed to surpass the incumbents (NX, CATIA, Creo, SolidWorks, Fusion, Onshape, Ansys, Abaqus, COMSOL, Altium, KiCad, Mastercam, hyperMILL, Teamcenter, Windchill) and the AI-built clones, be consistent and elegantly designed (design choices beyond the current spec are welcome), be implemented entirely in Rust, and read well for humans.

Founder directions for round 4 (2026-10-12): agents author designs and nobody models by hand, so the human UI is a viewer first: fast, beautiful inspection of geometry and results, review of agent work, and presentation output (photoreal renders, animations, exploded views, simulation visuals, shareable web views, generated decks and reports); people steer by pointing, marking up and asking. The polish reference is "Anatomy" (github.com/wheresryan22/anatomy, MIT; read its `SKILL.md` and `references/craft.md`): editorial serif typography on a calm canvas, fine-line isometric technical drawings with labelled callouts, real 3D motion with moving parts you can rotate and inspect, and physically convincing effects (fire, fluid, plasma) from shaders; Crucible delivers that level through its own Rust renderer, applied to real engineering geometry and simulation results. Reverse engineering (REA) is for insight only: study how incumbents work to design something far better from the literature, never copy code.

1. **Third review.** Nine reviewers on `docs/review/brief.md`: R13 physics, R14 geometry, R15 architecture and elegance, R16 engineering practice, R17 security and legal, R18 feasibility and the Rust implementation, R19 competitive parity for design, manufacturing and PLM, R20 competitive parity for simulation and electronics, R21 editorial (human reading). Then `python3 docs/tools/findings.py`.
2. **Contract v7** rules on findings that target CONTRACT, and the contract itself gets an editorial pass.
3. **Packets and one revision per tab** on `docs/revision/brief.md`, including an editorial polish of the whole tab.
4. **Audited consistency pass**, then the summary tabs (Overview, Adversarial review, Decisions log), publishing, and the tag `round-4`.
5. **Then phase 0** starts in this repository; outside inputs (counsel, partner agreements) proceed in parallel.

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

- One commit per tab revision: `<TAB> v2: revise against contract v4.x and <n> review findings`. The body lists declined findings with reasons, decisions added and revised, and the word count.
- Contract commits: `Contract v<x>: <what was ruled>`.
- Push each commit to `origin` after the check passes. Never rewrite published history.
