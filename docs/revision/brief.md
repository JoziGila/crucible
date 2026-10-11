# Round 2: revise a tab (brief for each tab's revision agent)

Six adversarial reviewers attacked the round 1 drafts and found 295 problems, 23 of them Critical. The contract is now v4.1 and binding. Your job: revise your tab so it conforms to the contract and fixes every finding in your packet, cut it to length with taste, and pass the spec check. Anvil (`docs/spec/02-anvil.md`) and Flux (`docs/spec/03-flux.md`) are already revised; they show the target shape.

## 1. Read

1. `docs/contract.md`, in full. It changed substantially since round 1: two identities (`GeometryId` and `ObjectId`), text-derived `OpSite`, label invariance, the label lattice and context labels, `Failure` versus `Abort`, error budgets and `CheckOutcome`, physical safety and Act approvals, the two worker pools, the per-region Flux discretization, kernel IR phasing, the Ingot executor, iPadOS, Tier 1 preview targets, the program plan and phase 1 scope (13.2), performance targets on a fixed reference laptop (13.3), std package names and the glossary's "Never call it" column. Section 16 lists the changes since v4.
2. Your packet, `docs/revision/packets/<TAB>.md`: the round 1 edits, the round 2 contract changes for your tab, and every finding that targets your tab.
3. Your round 1 draft, `docs/spec/<file>.md`. It is also kept at the `round-1` tag: `git show round-1:docs/spec/<file>.md`.
4. The lead, one design section and the tail sections of `docs/spec/02-anvil.md` or `docs/spec/03-flux.md`, for shape and voice. Do not copy their content; point to them where they own a fact.
5. Ingot only: `docs/revision/wip/01-ingot.partial.md` is a partial revision (lead, scope and the start of lexical syntax) written after reading the packet. Continue from it or replace it.

## 2. Revise

Write parts under `docs/build/<tab>/` (ignored by git), each under about 4,000 words, and assemble the finished tab over `docs/spec/<file>.md`. Keep the title line `# <tab name> (<TAB>)`.

- Apply every finding in your packet unless you have a sound reason not to. Record each declined finding, with its id and reason, under Open questions or Contract change requests.
- Conform to the contract everywhere: names, types, phases, golden products, class names and targets. Where your draft cites a number or rule the contract now fixes, use the contract's.
- Follow the skeleton in contract section 11 exactly: a lead with no heading; design sections, each ending with one capability table (Capability · Contract · Failure · Oracle id · Phase) and no separate catalog sections; State of the art; Platform notes; Interfaces with other subsystems; Oracles (each oracle once: id · verifies · pass criterion); Phasing (gate contributions only, consistent with section 13); Open questions; Contract change requests; Sources.
- Decision numbers are stable. A reversed or changed decision keeps its number, states the new decision and ends with "(revised in round 2)". New decisions take the next free number. Never cut a decision.
- Length: 12,000 to 18,000 words excluding Sources (Ingot and Anvil up to 20,000). Cut repetition, restated rationale, content another tab owns (one line plus a pointer instead) and prose that a table already says. Never cut a capability, decision, oracle or source.
- Taste: contract section 10. Present tense, precise, calm; no hype words; sentences under 25 words where possible; paragraphs of at most three sentences; specifics over adjectives.
- Diagrams: at most two, marked `[[DIAGRAM: <what to draw>]]`. A drawn diagram's marker becomes `[[DIAGRAM diagrams/<file>.jsx: <caption>]]`, with the widget source in `docs/spec/diagrams/`.
- Research: cite only pages you opened with WebFetch; mark anything unverified with [unverified]; never invent version numbers, dates, statistics or customer names.
- Write only your own `docs/spec/<file>.md` and `docs/build/<tab>/`. Never edit another tab, the contract, a README or CLAUDE.md, and never commit; the orchestrator does that.

## 3. Check

```
python3 docs/tools/check.py docs/spec/<file>.md --base round-1
```

It must report zero errors. It checks retired names, `Field` arity, fidelity names, HTML, table shape, the skeleton, one capability table per design section, oracle definitions and references, decision numbering and anything cut since round 1. Then read its warnings (length, long sentences, long paragraphs, uncited oracles) and fix the ones that read better fixed.

Also check by reading: "component" never means a catalog part; "Op" never means an API method; fidelity names are only `Preview`, `Interactive` and `SignOff`; every cross-tab fact matches its owning tab. A deliberate quotation of a forbidden term needs a line in `docs/tools/allow.txt`; say why in your report.

## 4. Report

Reply in at most 250 words: the file and its word count excluding Sources; findings applied and declined (list declined ids with one-line reasons); decisions added and revised; contract change requests filed; the check result; anything blocked.
