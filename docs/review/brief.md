# Adversarial review brief (shared by all six reviewers)

This is the brief for the second review, of the revised spec at tag `round-2`. The first review's brief is at tag `review`.

You are one of six adversarial reviewers of the Crucible platform spec: the binding contract v5 (`docs/contract.md`) and twelve revised subsystem tabs (`docs/spec/01-ingot.md` to `12-platform-performance.md`, about 218,000 words), in the repository /Users/jozigila/Code/crucible. Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from one typed model. The founder's hard requirements: design and simulate anything physical (with honest validity limits), state-of-the-art optimized methods everywhere, every major OS with identical features, and supreme coherence and taste. The spec must be complete enough that an engineering team and agent swarms working against oracles could build it without further design work.

Your job is to find what is still wrong, missing, inconsistent, infeasible, below the state of the art, unsafe, legally risky, unbuildable or tasteless, and to propose a concrete fix for each. Do not praise. Do not restate the tabs.

## Read first

1. The contract in full. Sections 14 to 16 are the rulings so far; do not re-report them. Do report a ruling that is wrong.
2. `docs/spec/13-adversarial-review.md`: how the first review's 295 findings were resolved or declined. Do not re-report a finding that its resolution fixed. Do report a fix that does not hold, a fix that created a new problem, and a declined finding whose stated reason is wrong.
3. Your primary tabs in full, then the sections of other tabs your angle touches (each tab's lead, capability tables, Interfaces, Phasing and Open questions; use Grep and Read with offsets on the `## ` headings).

## What to look for, beyond the first review's list

- **Buildability.** A capability whose contract, types, failure behaviour or oracle is too vague to build against, or an oracle whose pass criterion is not machine-checkable.
- **Open questions.** For each open question in your area, propose an answer: a finding whose Fix is the decision, with its reason. Name the question by tab and number.
- **Unverified claims.** Verify the `[unverified]` claims in your area with WebFetch on primary sources (standards bodies, vendor docs, project repositories, papers). A refuted or outdated claim is a finding. A claim you confirm goes in the Verified section below. WebSearch quota may be exhausted; do not depend on it. Cite only pages you opened.

## Output

Write your report to the file named in your assignment, in this exact format, findings most severe first:

```
# R<n> <lens> review

Summary: <five lines at most: the three most serious problems>

### R<n>-<nn> · <Critical|Major|Minor> · Targets: <tab codes, comma-separated>
**Section:** <tab section heading(s), or "Open questions <n>">
**Problem:** <what is wrong, one to four sentences>
**Evidence:** <URL you opened, a quote from a tab, or precise reasoning>
**Fix:** <the concrete change: replacement decision, new requirement, exact wording, design, or cut>

## Verified claims

- <TAB>: <the claim, a few words, as the tab states it> | <URL you opened>
```

Tab codes: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, and CONTRACT for the contract itself.

Severity:
- **Critical**: breaks a founder requirement, a principle or the architecture; a false or dangerous claim; something that cannot work or cannot be built as specified.
- **Major**: a significant gap, an inconsistency between tabs, a method clearly below the state of the art, an infeasible target, a missing capability practitioners need, or an open question that blocks building.
- **Minor**: a local precision, wording or ordering problem.

Write 25 to 60 findings. Each fix must be actionable by the tab's author without further research where possible. Write a long report in parts of at most about 4,000 words under `docs/build/review/` and assemble it. Do not edit the tabs, the contract or the Claude Doc, and never commit.

When done, reply in at most 200 words: the file path, counts by severity, the number of verified claims, and your three most serious findings.
