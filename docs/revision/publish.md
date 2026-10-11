# Publishing to the Claude Doc

The repository is the source of truth. The Claude Doc [Crucible — Platform Spec](https://claude.ai/code/artifact/bb8a8fb2-1060-40c5-98b7-fe5ef6148a0c) is its published view, one doc tab per file in `spec/`. Publish a tab only after its commit lands, and record the publish in README.md's status table.

Publishing needs the Claude Docs tools (`guide`, `read`, `update`, `batch`). If the session has none, skip publishing; a claude.ai session with the repo's files can publish later.

## Ids

Container for every call: `{"kind":"project","id":"bb8a8fb2-1060-40c5-98b7-fe5ef6148a0c"}`. Pending block ids are full ids (the outline view abbreviates `mb936hgtven.15` to `.15`).

| Doc tab | Repo file | Tab file id | Prose node id | State on 2026-10-11 |
| --- | --- | --- | --- | --- |
| Overview | `spec/00-overview.md` | `cd99b18e-5c88` | `650a6e1d-d481` | Published (pre-review). Widgets `541263cc-6217` (architecture), `5752d02f-60a3` (roadmap) |
| Subsystem specs | index of the twelve tabs | `113d0e89-a884` | `f7446683-6382` | Published; its ECO line says "plugins", which the glossary forbids: change it to "extensions" at the next publish |
| Ingot language | `spec/01-ingot.md` | `a7d27ecb-b645` | `2ce2e496-cb52` | Pending block `mb936hgtven.15` |
| Anvil geometry kernel | `spec/02-anvil.md` | `1ca33b99-5780` | `6167cdda-af0b` | Published (v2). Widgets `b823678b-5f57` (lattice), `41c025a6-515f` (two-stage operation) |
| Flux physics engine | `spec/03-flux.md` | `60fe18e0-b55b` | `20fac20b-7ecb` | Pending block `mb936hgtven.20` |
| Physics coverage and materials | `spec/04-coverage.md` | `2cd43e57-2f23` | `960ad32b-62d7` | Pending block `mb936hgtven.31` |
| Kiln, repository and PLM | `spec/05-kiln-repo-plm.md` | `239dfa78-766a` | `0239c2e0-2299` | Pending block `mb936hgtven.25` |
| Mechanical design | `spec/06-mechanical.md` | `7a011aa1-848c` | `85446926-a811` | Pending block `mb936hgtven.18` |
| Manufacturing | `spec/07-manufacturing.md` | `c68d75b3-c828` | `49f64c61-1557` | Pending block `mb936hgtven.14` |
| Electronics and systems | `spec/08-electronics-systems.md` | `fc2ec3b8-0935` | `d653a3ba-9b55` | Pending block `mb936hgtven.24` |
| Agents | `spec/09-agents.md` | `a6f677b5-4d2d` | `cc3af25b-9467` | Pending block `mb936hgtven.7` |
| UI and interaction | `spec/10-ui.md` | `86708451-ba38` | `2db4aa8f-a611` | Pending block `mb936hgtven.19` |
| Interop and ecosystem | `spec/11-interop-ecosystem.md` | `84c37544-9d54` | `3b551788-4815` | Pending block `mb936hgtven.22` |
| Platform and performance | `spec/12-platform-performance.md` | `c4ec8f14-d594` | `b60a1de5-077c` | Pending block `mb936hgtven.25` |
| Adversarial review | `spec/13-adversarial-review.md` | `e4ae4c32-ca51` | `68c9752c-b279` | Pending block `mb936hgtven.19` |
| Decisions log | `spec/14-decisions-log.md` | `cba5bdcd-a313` | `f5f266e1-b97b` | Pending block `mb936hgtven.14` |

## First publish of a tab with a pending block

1. Load the guides: `guide` with `items: ["topic.index"]`, then a separate call with `items: ["topic.diagram"]`. Follow them.
2. Drop the file's title line; the tab already shows its title.
3. First call: one `update` on the prose node (`ref: {"object":"node","id":"<node id>"}`, `engine: "prose"`) with one `replace` op whose target is `{"kind":"blocks","ids":["<pending block id>"]}` and whose `with` is `{"from":{"kind":"inline","content":"<lead>\n\n## <first section>\n\n…"},"as":"markdown"}`. A pending block needs no guard.
4. Then one `update` per further `##` section, in order: an `insert` op with `target: {"kind":"root"}`, `side: "end"` and `source: {"from":{"kind":"inline","content":"## <section>\n\n…"},"as":"markdown"}`. Split a section over about 4,000 words at a `###` boundary.
5. Diagrams: for each `[[DIAGRAM diagrams/<file>.jsx: <caption>]]`, one `batch` that creates the widget from that file's code (parent: the tab file id) and inserts its embed block with the caption, followed by the paragraph that reads the diagram. Then take a screenshot `read` of the widget and fix any overlap, clipped text or crossing line. A marker still in the form `[[DIAGRAM: …]]` is drawn first; save its source under `spec/diagrams/` and update the marker in the same commit.
6. Markdown only: headings, tables, lists, code blocks, links, bold. No HTML. Display formulas go in `latex` code blocks.
7. Never write to another tab, never use `force`, never delete content you did not write. If a call is refused, read the refusal code, fix the call and resend it.
8. Finish with a `read` of the node (`engine: "prose"` at call level and in the payload, `payload: {"projection":"outline"}`) and confirm every section landed once, in order, with no pending block left.

## Republishing a published tab

Overview and Anvil are published. Read `topic.editing` first, then replace each changed section in place. Keep a widget node when its source file is unchanged, and update its code when the file changed.
