# Round 3: revise a tab (brief for each tab's revision agent)

A second adversarial review attacked the v2 tabs and found 278 problems, 16 of them Critical. Contract v6 rules on every finding that targets it (section 17) and is binding. Your job: revise your tab once so it conforms to contract v6, fixes every finding in your packet, closes its open questions and settles its `[unverified]` claims, while staying within its length and passing the spec check.

## 1. Read

1. `docs/contract.md`: section 17 in full, then every section it changed, then anything your packet's findings touch.
2. Your packet, `docs/revision/packets/<TAB>.md`: the findings that target your tab, the claims reviewers verified, every `[unverified]` line, your open questions and your known items.
3. Your tab, `docs/spec/<file>.md` (v2, tag `round-2`). The review reports behind your findings are `docs/review/R7-physics.md` to `R12-feasibility.md`.
4. For any fact another tab owns, that tab's committed text (`git show HEAD:docs/spec/<file>.md`); point to it in one line instead of restating it.

## 2. Revise

Write parts under `docs/build/<tab>/` (ignored by git), each under about 4,000 words, and assemble the tab over `docs/spec/<file>.md`. Keep the title line `# <tab name> (<TAB>)`.

- **Findings.** Apply each one unless you have a sound reason not to; where contract 17 already settles it, conform to the ruling. Record each declined or partly applied finding, with its id and reason, under Open questions.
- **Open questions.** Close each one: decide it (as a decision, new or revised), turn it into a contract change request, or keep it with the reason it cannot be decided yet.
- **Unverified claims.** Verify each with WebFetch on a primary source and drop the marker, correct the claim, or cut it. Cite only pages you opened, and keep every existing source.
- **Known items.** Do each one in your packet, including one sentence under each drawn diagram that tells the reader how to read it. If a fix changes a diagram, update its file in `docs/spec/diagrams/` too.
- **Shape.** Follow contract sections 10 and 11 exactly: a lead with no heading; design sections, each ending with one capability table (Capability · Contract · Failure · Oracle id · Phase); State of the art; Platform notes; Interfaces with other subsystems; Oracles; Phasing (cite 13.4 once); Open questions; Contract change requests; Sources.
- **Decisions.** Numbers are stable and no decision is cut. A changed decision keeps its number, states the new decision and ends with "(revised in round 3)", replacing any earlier marker. New decisions take the next free number.
- **Length.** 12,000 to 18,000 words excluding Sources (Ingot and Anvil up to 20,000). Your tab is near its ceiling, so make room by cutting repetition, restated rationale and anything another tab owns. Never cut a capability, decision, oracle or source.
- **Program.** Crucible is built by agents with one founder (contract 13.2). Remove every staffing figure, hire, team size, engineer-year and calendar month; refer to milestones and gates in order instead.
- **Voice.** Contract section 10: present tense, precise and calm; sentences under 25 words where possible; paragraphs of at most three sentences; specifics over adjectives.
- Write only your own `docs/spec/<file>.md`, your diagram files and `docs/build/<tab>/`. Never edit another tab, the contract, a README or CLAUDE.md, and never commit; the orchestrator does that.

## 3. Check

```
python3 docs/tools/check.py docs/spec/<file>.md --base round-2
```

It must report zero errors; `--base round-2` also reports any decision, oracle or source cut since round 2. Then fix the warnings that read better fixed. A deliberate quotation of a forbidden term needs a line in `docs/tools/allow.txt`; say why in your report.

## 4. Report

Reply in at most 250 words: the word count excluding Sources; findings applied and declined (declined ids with one-line reasons); open questions closed and kept; unverified claims verified, corrected and cut; decisions added and revised; contract change requests filed; the check result; anything blocked.
