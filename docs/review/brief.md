# Adversarial review brief (shared by all nine reviewers)

This is the brief for the third review, of the spec at tag `round-3`. Earlier briefs are at tags `review` and `second-review`.

You are one of nine reviewers of the Crucible platform spec: the binding contract v6.1 (`docs/contract.md`), twelve subsystem tabs (`docs/spec/01-ingot.md` to `12-platform-performance.md`, about 216,000 words) and the Overview (`docs/spec/00-overview.md`), in the repository /Users/jozigila/Code/crucible. Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from one typed model. It is implemented entirely in Rust and built by agent swarms against oracles, directed by one founder (contract 13.2).

This is the last review before building starts. The bar has three parts:

1. **Better than everything.** A working engineer who uses Siemens NX, CATIA, Creo, SolidWorks, Fusion, Onshape, Ansys, Abaqus, COMSOL, Altium, KiCad, Mastercam, hyperMILL, Teamcenter or Windchill finds nothing they rely on missing, and finds clear reasons Crucible is better. AI-built clones (SolidCraft, the ArtCraft "Craft" apps, Zoo) already copy interfaces in days; Crucible must win on what they cannot copy quickly.
2. **Elegant.** One concept per name, one fact per place, the fewest mechanisms that do the job, and a design a strong Rust team would be proud of. You may propose design choices beyond the current spec: replace a mechanism, merge two, cut one. Say what to delete and why the result is simpler or stronger.
3. **A pleasure to read.** A human engineer reads each tab start to finish and understands it: a clear lead, sections that build on each other, terms defined before use, examples where they help, and no wall of qualifications.

Your job is to find what falls short of that bar and propose a concrete fix for each. Do not praise. Do not restate the tabs.

## Read first

1. The contract in full; sections 14 to 17 are the rulings so far. Do not re-report a ruling; do report one that is wrong.
2. `docs/spec/13-adversarial-review.md`: how both earlier reviews were resolved. Report a fix that does not hold or that created a new problem.
3. Your primary tabs in full, then the sections of other tabs your angle touches (use Grep and Read with offsets on the `## ` headings).

## Fact-checking

Verify load-bearing claims in your area with WebFetch on primary sources (vendor documentation, standards bodies, project repositories, papers). A refuted or outdated claim is a finding. Cite only pages you opened. WebSearch quota may run out; do not depend on it.

## Output

Write your report to the file named in your assignment, in this exact format, findings most severe first:

```
# R<n> <lens> review

Summary: <five lines at most: the three most serious problems>

### R<n>-<nn> · <Critical|Major|Minor> · Targets: <tab codes, comma-separated>
**Section:** <tab section heading(s)>
**Problem:** <what is wrong, one to four sentences>
**Evidence:** <URL you opened, a quote from a tab, or precise reasoning>
**Fix:** <the concrete change: replacement design, new capability with its phase, exact wording, or cut>
```

Tab codes: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, OVERVIEW, and CONTRACT for the contract itself.

Severity:
- **Critical**: breaks a founder requirement, a principle or the architecture; a false or dangerous claim; something that cannot be built as specified; or a gap that would make a serious engineer choose an incumbent instead.
- **Major**: a significant gap or inconsistency, a method clearly below the state of the art, a missing capability practitioners need, a design that has a clearly simpler or stronger alternative, or a section a careful reader cannot follow.
- **Minor**: a local precision, wording, ordering or readability problem.

Write 25 to 60 findings. Each fix must be actionable by the tab's author without further research where possible. Write a long report in parts of at most about 4,000 words under `docs/build/review/` and assemble it. Do not edit the tabs, the contract or the Claude Doc, and never commit. Never put personal data (names, emails) in any request you make.

When done, reply in at most 200 words: the file path, counts by severity, and your three most serious findings.
