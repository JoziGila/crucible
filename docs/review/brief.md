# Adversarial review brief (shared by all six reviewers)

You are one of six adversarial reviewers of the Crucible platform spec: twelve subsystem drafts (about 290,000 words) in /tmp/claude-0/-home-claude/bb4d35f7-5e7e-59c8-ab89-15471312d883/scratchpad/spec/ (files 01-ingot.md to 12-platform-performance.md). Crucible is one Rust platform where people and agents design, simulate, manufacture and release physical products from one typed model. The founder's hard requirements: design and simulate anything physical (with honest validity limits), state-of-the-art optimized methods everywhere, every major OS with identical features, and supreme coherence and taste.

Your job is to find what is wrong, missing, inconsistent, infeasible, below the state of the art, unsafe, legally risky or tasteless, and to propose a concrete fix for each. Do not praise. Do not restate the drafts.

## Read first

1. The binding contract v3: spec/00-contract.md. The drafts were written against v2. Section 14 lists rulings and the edits each tab will make; do not re-report those. Do report if a ruling itself is wrong.
2. Your primary drafts in full, then your targeted sections (use Grep and Read with offsets; drafts have `## ` headings).
3. Optional cross-tab context: spec/extracts/decisions.md (every decision), interfaces.md, ccr.md, open-questions.md.

## Fact-checking

Verify the load-bearing factual claims in your area, especially those marked [unverified], with WebFetch on known primary URLs (standards bodies, vendor docs, project repositories, papers). WebSearch quota may be exhausted; do not depend on it. Cite only pages you opened. A refuted or outdated claim is a finding.

## Output

Write your findings to the file named in your assignment, in this exact format, most severe first:

```
# R<n> <lens> review

Summary: <five lines at most: the three most serious problems>

### R<n>-<nn> · <Critical|Major|Minor> · Targets: <tab codes, comma-separated>
**Section:** <tab section heading(s)>
**Problem:** <what is wrong, one to four sentences>
**Evidence:** <URL you opened, a quote from a draft, or precise reasoning>
**Fix:** <the concrete change: replacement decision, new requirement, exact wording, design, or cut>
```

Tab codes: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, and CONTRACT for the contract itself.

Severity:
- **Critical**: breaks a founder requirement, a principle or the architecture; a false or dangerous claim; something that cannot work as specified.
- **Major**: a significant gap, an inconsistency between tabs, a method clearly below the state of the art, an infeasible target, or a missing capability practitioners need.
- **Minor**: a local precision, wording or ordering problem.

Write 25 to 60 findings. Each fix must be actionable by the tab's author without further research where possible. Do not edit the drafts or the shared Claude Docs document.

When done, reply in at most 200 words: the file path, counts by severity, and your three most serious findings.
