# Round 4: revise a tab (brief for each tab's revision agent)

This is the last revision before building starts. A third review by nine reviewers found 312 problems, 18 of them Critical, including two reviews that compared Crucible feature by feature with the incumbents and an editorial review for human reading. Contract v7 rules on every finding that targets it (section 18), simplifies the design and sets a new house style (sections 10 and 11). Your job: make your tab correct, complete against the incumbents, as simple as it can be, and a pleasure for an engineer to read from start to finish.

## 1. Read

1. `docs/contract.md`: sections 10 and 11 (the new style and skeleton), section 18 (rulings), 13.4 (shared phases and the parity floor), 7.7 (the adopt-or-study list and the clean-room insight protocol), then every section your packet's findings touch. `CLAUDE.md` lists the founder's directions for round 4.
2. Your packet, `docs/revision/packets/<TAB>.md`: the third-review findings that target your tab, its open questions and known items.
3. Your tab, `docs/spec/<file>.md` (v3, tag `round-3`), and the review reports behind your findings (`docs/review/R13-physics.md` to `R21-editorial.md`). R21 has rewritten leads and examples for several tabs.
4. `docs/revision/digest.md`: software to adopt, run as oracles, or study for your tab.
5. For any fact another tab owns, that tab's committed text (`git show HEAD:docs/spec/<file>.md`); link to it instead of restating it.

## 2. Revise

Write parts under `docs/build/<tab>/` (ignored by git), each under about 4,000 words, and assemble the tab over `docs/spec/<file>.md`. Keep the title line `# <tab name> (<TAB>)`.

- **Findings.** Apply each one, or conform to contract 18 where it settles one. You may choose a better design than a finding proposes when it is simpler or stronger; say so in your report. Declined parts go in your report, not in the tab.
- **Better than everything.** Cover every capability contract 13.4's parity floor assigns to your tab, at its phase, and say plainly in the lead and the relevant sections what the engineer gains over the incumbents and over AI-built clones.
- **Simplify.** Where two mechanisms in your tab do one job, merge them; where a mechanism no longer earns its place, delete it. Keep every capability the contract requires.
- **Restructure to section 11.** A three-sentence lead in plain words; a first, guide-level design section that opens with a worked example (the canonical bracket or a golden product) and explains the model a user meets; later sections that build on it, each opening with why it exists and ending with its capability table; catalogs, grammars and code tables moved into `## Reference`; Interfaces as one provides table (To · What · Types · Phase); Oracles without a phase column; Open questions only for questions that wait on an outside input.
- **No history in the prose.** Remove every review finding id, round number, "(revised in round N)", "formerly" and "replaces" above `## Open questions`. Decisions keep their numbers, in the three-line block (Decision, *Why:*, *Rejected:*); a changed decision simply states its new content.
- **Write for a person.** Define every term and abbreviation at first use; one idea per paragraph; examples where they help; tables for comparisons; no wall of qualifications. Read your lead and first section aloud in your head: an engineer from outside your subsystem must follow them.
- **Facts.** Cite only pages you opened with WebFetch; mark anything unverified with [unverified]; never invent numbers, dates or names. Keep every existing source unless the claim it supported is cut.
- **Diagrams.** At most two. Update a diagram's file in `docs/spec/diagrams/` when its content changes, and keep one sentence under each that tells the reader how to read it.
- **Length.** 9,000 to 15,000 words of prose (ING and ANV up to 17,000); tables, Reference, State of the art, Interfaces, Oracles and Sources do not count.
- Write only your own `docs/spec/<file>.md`, your diagram files and `docs/build/<tab>/`. Never edit another tab, the contract, a README or CLAUDE.md, and never commit.

## 3. Check

```
python3 docs/tools/check.py docs/spec/<file>.md --base round-3
```

It must report zero errors: the skeleton, tables, decision blocks, the history ban, the prose length, and nothing cut since round 3 (a capability, decision, oracle or source). Then fix the warnings that read better fixed.

## 4. Report

Reply in at most 250 words: prose word count; findings applied and declined (declined ids with one-line reasons); designs you changed beyond the findings and what you deleted; parity-floor capabilities added; open questions left; decisions added and changed; contract change requests; the check result.
