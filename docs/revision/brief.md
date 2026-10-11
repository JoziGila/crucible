# Round 2: revise and publish (shared brief for the twelve tab authors)

Six adversarial reviewers attacked the drafts and found 295 problems, 23 of them Critical. The contract is now v4 and binding. Your job: revise your tab to conform to contract v4 and fix every finding in your packet, cut it to length with taste, then publish it into your tab of the shared spec document.

## 1. Read

1. `spec/00-contract.md` (v4), in full. It changed substantially since you drafted: two identities (`GeometryId` and `ObjectId`), text-derived `OpSite`, label invariance, the label lattice and context labels, `Failure` versus `Abort`, error budgets and `CheckOutcome`, physical safety and Act approvals, the two worker pools, the per-region Flux discretization, kernel IR phasing, the Ingot executor, iPadOS, Tier 1 preview targets, the program plan and phase 1 scope (section 13.2), performance targets with a fixed reference laptop (section 13.3), std package names, and the glossary's "never call it" column.
2. Your packet: `spec/reviews/packets/<TAB>.md` (round 1 edits, round 2 contract changes for your tab, and every finding that targets your tab).

## 2. Revise

Write the revised tab to `spec/<your file>.v2.md` and keep v1 for reference.

- Apply every finding in your packet unless you have a sound reason not to. Record each declined finding, with its id and reason, under Open questions or Contract change requests.
- Conform to contract v4 everywhere, including names, types, phases and targets. Where your v1 cited a number or rule that the contract now fixes (targets, phases, golden products, class names), use the contract's.
- Follow the skeleton in contract section 11 exactly: a lead with no heading; design sections, each ending with one capability table (Capability · Contract · Failure · Oracle id · Phase) and no separate catalog sections; State of the art; Platform notes; Interfaces with other subsystems; Oracles (each oracle once: id · verifies · pass criterion); Phasing (gate contributions only, consistent with section 13); Open questions; Contract change requests; Sources.
- Decision numbers are stable. A reversed or changed decision keeps its number, states the new decision and ends with "(revised in round 2)". New decisions take the next free number.
- Length: 12,000 to 18,000 words excluding Sources (Ingot and Anvil up to 20,000). Cut repetition, restated rationale, content another tab owns (one line plus a pointer instead) and prose that a table already says. Never cut a capability, decision, oracle or source.
- Taste: contract section 10. Present tense, precise, calm; no hype words; sentences under 25 words where possible; paragraphs of at most three sentences; specifics over adjectives.

Self-check before publishing. `grep -nE` your v2 for each of these and fix every hit that is not a deliberate quotation:

```
cpu-f64|wgpu-f32|cuda-f64|rocm-f64|\bSBOM\b|Indeterminate|ExecMode|crucible\.lock|std::flux|std::elx|std::sys\b|std::mat\b|std::phys\b|flux-field|flux-kernels|flux-bridges|anvil::bend|Zoo's patent|\bCircuit\b|sign-off mode|Govern|epoch interruption|operation catalog
```

Also check by reading: no `Field` with three type parameters (use product domains such as `Field<(Body, Time), Temperature>`); "component" never means a catalog part; "Op" never means an API method; fidelity names are only `Preview`, `Interactive`, `SignOff`.

## 3. Publish

The shared spec is a Claude Docs document. Load the tools with ToolSearch: `select:mcp__Claude_Docs__guide,mcp__Claude_Docs__update,mcp__Claude_Docs__batch,mcp__Claude_Docs__read`. Then call `mcp__Claude_Docs__guide` with `items: ["topic.index"]`, and in a separate call `items: ["topic.diagram"]`, and follow them.

- Container for every call: `{"kind":"project","id":"bb8a8fb2-1060-40c5-98b7-fe5ef6148a0c"}`. Your message gives your tab's prose node id, its pending block id and its tab file id. Your tab already shows its title as a heading; never repeat it.
- First call: one `update` on your prose node (`ref: {"object":"node","id":"<node id>"}`, `engine: "prose"`) with one `replace` op whose target is `{"kind":"blocks","ids":["<pending block id>"]}` and whose `with` is `{"from":{"kind":"inline","content":"<lead paragraph>\n\n## <first section>\n\n…"},"as":"markdown"}`. A pending block needs no guard.
- Then one `update` per further `##` section, in order: an `insert` op with `target: {"kind":"root"}`, `side: "end"` and `source: {"from":{"kind":"inline","content":"## <section>\n\n…"},"as":"markdown"}`. If a section exceeds about 4,000 words, split it at a `###` boundary into two calls.
- Diagrams: replace each `[[DIAGRAM: …]]` marker with a drawn widget, following topic.diagram exactly: one `batch` that creates the widget (parent: your tab file id) and inserts its embed block at the end of the tab, with the sentence of reading under it. Then take a screenshot `read` of the widget and fix any overlap, clipped text or crossing line before moving on. At most two diagrams.
- Markdown only: headings, tables, lists, code blocks, links, bold. No HTML. Display formulas as ```latex code blocks.
- Never write to another tab, never use `force`, never delete content you did not write. If a call is refused, read the refusal code, fix the call and resend it.
- When done, `read` your node with `payload: {"projection":"outline"}` and confirm every section landed once, in order, with no pending blocks left.

## 4. Report

Reply in at most 250 words: the v2 file path and word count (excluding Sources); findings applied and declined (list the declined ids with one-line reasons); decisions added and revised; publishing status (sections published, diagrams drawn and checked); anything blocked.
