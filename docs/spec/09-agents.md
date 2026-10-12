# Agents (AGT)

Agents in Crucible are colleagues on branches: they call the same typed `api` that a person's clicks call, and hand their work over as Proposals, branches that a human reviews like pull requests. Incumbent copilots answer questions or edit the open model on the user's behalf; a Crucible agent's work arrives built, checked, attacked by an independent verifier and classed by risk. Safety lives in the server, not in the model: untrusted text never carries authority, and nothing leaves Crucible until a named human approves its exact plan.

## An agent's task, step by step

This section follows one agent through one small task on the canonical bracket of contract section 6, so that every later section fills in a step the reader has already seen.

### Widening the bracket

A designer asks an agent to widen the bracket to 80 mm for a new mounting pattern. The agent runs in any MCP host, an AI application that calls tools over the Model Context Protocol; here it is a coding agent on the designer's laptop.

1. **Open a session.** The agent calls `session.open` with the role `std::agents::detail_designer@1`, a new branch `widen-bracket` forked from `main`, the scopes it needs and a budget of 5 USD. The server intersects the request with the designer's own permissions and returns a session handle, the effective grant, the budget account and the model context's label: `internal`, with no integrity flags yet ([Sessions](#principals-and-sessions)).
2. **Read.** `read.outline` on `bracket` returns its parameters with types and ranges (`width: Length in 20mm..=400mm = 60mm`), its features and its named check `static_margin`. Text that the designer's team typed in Crucible comes back as text; a name from an imported supplier file would come back as a handle the agent cannot read as instructions ([Labels and injection defence](#labels-and-injection-defence)).
3. **Edit.** `edit.apply` sends `SetParameter { target: bracket, param: width, value: 80mm }` against the branch head. The server lowers the edit to an Ingot source patch, formats it, compiles it, records one Change and returns the patch ([Edits and concurrency](#edits-and-concurrency)):

   ```
   -    width: Length in 20mm..=400mm = 60mm,
   +    width: Length in 20mm..=400mm = 80mm,
   ```

4. **Evaluate.** `evaluate.ci` runs exactly what Proposal CI will run and streams frames as Kiln computes them: the rebuilt Body, the stress Field with its error budget, and the check outcome. `static_margin` passes at `Interactive` fidelity and stays provisional until CI's `SignOff` run ([Evaluations and streams](#evaluations-and-streams)).
5. **Look.** `inspect.describe` answers from typed facts, with no model in the loop ([Observation](#observation)). Its brief form, with illustrative values:

   > Part `bracket`, aluminium 6061-T6. Bounding box 80.0 × 40.0 × 26.0 mm; mass 78 g ± 1 g. Features: sketch, extrude 6 mm, rib 20 mm, fillet 2 mm on the new edges. Checks: `static_margin` `Pass` at `Interactive`, provisional. Regularized peak von Mises stress at the web root: 74 MPa ± 7 MPa (`Estimated`) against a limit of 166 MPa.

   `inspect.render` adds a four-view Snapshot whose numbered marks map to entity ids, so "the edge marked 3" means one exact edge.
6. **Propose.** `propose.create` opens a Proposal from `widen-bracket` into `main` with a rationale ("widen for the 80 mm pattern") and a requirement link. The server refuses it unless the head builds, every check meets its gate, Snapshots exist at the head, the rationale is complete and every Change carries signed provenance ([Proposals and review](#proposals-and-review)).
7. **Attack.** An independent verifier, in a fresh context that never sees the author's free text, attacks the Proposal. It thins the web by half and sees `static_margin` fail, so the check is not vacuous; it evaluates the worst-case thickness of 5.9 mm; and it replays CI in a second platform class ([Roles](#roles)).
8. **Classify.** The server computes the risk class from the semantic diff. `width` moved inside its declared range on an unreleased design, no check, tolerance, bill-of-materials (BOM) line or dependency changed, and the margin rose, so the change is R1-shaped. The designer's laptop host is outside Crucible's model gateway, so its context is `Declared` and starts `data_untrusted`, and the class is R2. The same edit from the hosted crew would be R1, which the repository's auto-merge policy may merge after a quiet period ([Risk classes](#risk-classes)).
9. **Review and merge.** A reviewer outside the delegation chain opens the Proposal: width 60 → 80 mm, mass up by about 20 g, margin up, renders of both sides, the verifier's report. The reviewer approves with an approval credential, and `propose.merge` lands one Change on `main`.

Nothing in this story left Crucible. If the designer next wants a quote, the agent may prepare a `request_quote` Act, but only a named human approving its exact plan sends it ([Acts and approvals](#acts-and-approvals)).

### The model a user meets

Every step above used a handful of concepts, defined here once.

| Term | Meaning |
| --- | --- |
| Principal | Who calls: a person (`user:<id>`), an agent instance (`agent:<org>/<role>/<instance>`) or a service (`service:<name>`); an agent always acts for a human |
| Delegation chain | The principals from the delegating human (index 0) to the current actor, derived by the server from its own session lineage |
| Session | A server-minted handle binding a principal, a branch, a grant, a budget and a model context |
| Model context | The unit that accumulates a label: a hosted-crew conversation, or an external host's (user, client identity) pair (contract 7.6) |
| Context label | The join of the labels of every value the context has read: confidentiality, usage and integrity (contract 5.3) |
| Role | An Ingot record plus a skill: purpose, scopes, write-set rule, exit checks and outputs |
| Delegation grant | A signed, time-bound grant from a human to agents: scopes, repository, budget and expiry |
| Proposal | A branch plus rationale plus CI report; the unit of agent work and of human review |
| Risk class | R0 (no semantic change) to R4 (feeds an Act), computed by the server from a Proposal's semantic diff and its authoring contexts' labels |
| Assurance | `Attested` when the hosted crew or the model gateway saw every model call; `Declared` otherwise, so the host's model and tools are recorded as stated and never trusted |
| Clean context | A context with no integrity flag; only `Attested` contexts can be clean, and only clean contexts may auto-merge |
| Act | An API method whose effect needs a human Approval of an exact plan, because it reaches outside Crucible or publishes a record others rely on |

"Evaluation" always means a Kiln request, so measuring agents is called benchmarking.

Six invariants hold for every call, whatever model or host drives the agent:

1. **Parity of capability.** People, agents, the UI, the CLI and CI call the same methods; only accountable humans approve Acts, protected merges and signature records.
2. **Branch confinement.** Agents write only to unprotected branches; protected branches change only through Proposals.
3. **Proposals are the unit of agent work.** A Proposal enters review only after it builds, meets every check's gate and carries server-generated Snapshots.
4. **Enforcement lives in the server.** `api` checks scopes, budgets, labels and approvals on every call.
5. **No correctness depends on a model.** Every agent output becomes Ingot source or a typed record that deterministic checks verify.
6. **Every claim has an oracle.** Exit criteria are checks, and graders live in `oracles/agents/`, which agents may read and never write.

This tab owns the `api-schema` and `api` crates (the catalog, sessions, boundary labels, budgets, errors, audit payloads and Acts) and the services `apps/mcp`, `apps/crew` and `apps/model-gateway`. It also specifies observation, roles, swarms, Proposals, benchmarks and training data; Kiln, `repo`, `plm`, `trust`, Anvil, Flux and PLT own the machinery underneath. Phase 0 serves the catalog in single-principal mode, a local install with one person; scopes, labels, grants and approvals arrive with KLN's identity and authorization in phase 1.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Parity of capability | Every UI, CLI, CI and agent action is an API method; tool lists differ only by grant | A missing method fails the catalog coverage test | AGT-O-SDK-1 | 0 |
| Branch confinement | Agent sessions open only on unprotected branches | `session/branch_protected` | AGT-O-POL-1 | 1 |
| Server-side enforcement | Scopes, labels, budgets and approvals on every call; single-principal mode before phase 1 | Typed `auth`, `label` and `budget` errors | AGT-O-POL-1 | 1 |
| Checked outputs | Agent output lands as Ingot source or typed records that checks verify | `edit/introduces_errors`, `propose/preconditions_failed` | AGT-O-BENCH-1 | 1 |

## Sessions, edits and evaluations

An agent needs a handle that says whom it acts for, a way to change source that never loses an update, and results that stream while Kiln computes; this section specifies the three.

### One catalog

**Decision D-AGT-1:** The `api` method catalog is the only programmatic surface of Crucible: MCP tools, SDK methods, WIT functions, UI commands and CLI subcommands map one-to-one onto API methods.
*Why:* agents are first-class users, a second surface would drift from the first, and principle 1 forbids privileged paths.
*Rejected:* a separate agent API, which drifts and doubles testing; a code-only surface that runs scripts, which loses typed inspection, evaluation and review.

The catalog lives in two crates. `api-schema` holds the method types, the error namespace, the canonical codec, client stubs and transport traits, and depends only on the Contracts row of contract 12. `api` holds the implementations over `repo`, `plm`, `trust` and `kiln`. The engine process, the browser engine worker and the CLI's local mode link `api`; UI processes, the browser UI module, `sdk/rust` and the client side of `apps/mcp` link only `api-schema`, so no UI can call the engine in process. Like every crate under `core/`, `api` reads clocks and spawns tasks only through `platform-api`'s `Monotonic` and `Spawner`, so it runs unchanged in the browser engine worker.

Every method is `<group>.<name>` in contract 7.6's eight groups: Session, Read, Edit, Evaluate, Inspect, Compare, Propose and Act. The full catalog is in [Reference](#method-catalog).

### Principals and sessions

A session answers three questions on every call: who is calling, for whom, and with what authority. The server derives the delegation chain from its own session lineage, never from token `act` claims, which token exchange makes informational for nested actors [RFC 8693]. Remote transports use MCP's OAuth 2.1 profile with Client ID Metadata Documents, audience-bound tokens and step-up through `insufficient_scope` [MCP authorization].

**Decision D-AGT-3:** A session is an opaque 128-bit random handle bound to the principal and token issuer, expiring by default after 24 hours idle or 7 days; atomicity is per Change and isolation per branch, with no long-lived transaction.
*Why:* MCP recommends explicit handles, a handle never authenticates [MCP security practices], and cheap branches already isolate work.
*Rejected:* protocol-level sessions, which MCP removed; multi-call transactions with locks, which bring contention, leaked locks and a second concept beside branches.

```rust
pub struct SessionOpen {
    pub repo: RepoId,
    pub branch: BranchSpec,              // Existing(BranchName) | Fork { name, from: ChangeRef }
    pub role: Option<RoleRef>,           // "std::agents::detail_designer@1"
    pub scopes: Vec<Scope>,              // the effective grant is an intersection
    pub write_set: Option<WriteSet>,
    pub budget: Budget,
    pub purpose: String,                 // agent text, always shown as such
    pub grant: Option<DelegationGrantId>,// required for hosted-crew sessions
    pub work_item: Option<WorkItemId>,
}

pub struct SessionOpened {
    pub session: SessionHandle,
    pub head: ChangeId,
    pub grant: Grant,                    // effective scopes, write set, clearance, expiry
    pub budget: BudgetAccount,
    pub context: Labels,                 // the model context's label
}
```

The effective grant intersects the human's permissions, the role's scopes, repository policy and the request. The clearance is the meet of the human's, the client's or model endpoint's, and the policy's.

**Decision D-AGT-28:** Agents act under signed, time-bound delegation grants, and crew instances exchange tokens only against a live grant, only for agent scopes and only sender-constrained.
*Why:* otherwise one compromise of `apps/crew` yields authority over every delegating user.
*Rejected:* standing token exchange; bearer tokens for crew workers.

A grant names scopes, repository, budget and expiry. Token exchange never yields an Approval or `policy:admin`, and DPoP (demonstrating proof of possession) or mutual TLS binds each token to the client's key [RFC 9449].

Only the delegating human steers a running agent (`session.control`). Anyone else's @mention becomes a request in that human's inbox, with attachments as `ExternalText`, the type of untrusted text that is never read as instructions.

### Local credentials

A process acting for a person must never become that person. A credential held on a device, such as the desktop keychain or the CLI's saved session, authenticates without a fresh user-presence proof as the device agent `agent:<org>/local/<device>`, with `Declared` assurance, never as the human (contract 7.6).

A coding agent with a shell tool that runs `crucible` subcommands is therefore a local device agent. It may read, edit its own branches and propose, and its context is labelled like any external host's. Human-only methods need a WebAuthn (W3C Web Authentication) user-verification assertion on the approval origin (the separate web origin that serves only approval pages), bound to the call's argument digest and valid for one call:

- `propose.merge`, `propose.endorse_text`, `propose.policy`, `propose.declassify` and `propose.waive`;
- recipient-record and clearance changes;
- every local write of a payload above `public`.

The CLI opens the approval origin in a browser session for the assertion and fails with `auth/assertion_required` when none arrives. Source that arrives through the language server, a file import or any channel other than Crucible's own editor is untrusted until the person confirms the batch on the approval origin ([KLN, span provenance](05-kiln-repo-plm.md#span-provenance)). An AI extension in an editor thus produces untrusted spans, never "typed by a person" ones.

### Edits and concurrency

`edit.apply` applies a list of edits atomically and records one Change. Every edit lowers to an Ingot source patch, which the response returns.

```rust
pub struct ApplyEdits {
    pub session: SessionHandle,
    pub base: ChangeId,                  // exact; a stale base is handled by on_stale
    pub edits: Vec<Edit>,
    pub on_stale: OnStale,               // Fail | RebaseIfDisjoint (default)
    pub message: String,
    pub dry_run: bool,
    pub allow_errors: bool,              // own unprotected branches only
}

pub enum Edit {
    Patch { path: SourcePath, range: TextRange, expected: Sha256, replacement: String },
    SetParameter { target: FeaturePath, param: Ident, value: ParamValue },
    InsertFeature { after: FeaturePath, binding: Ident, call: IngotExpr },
    RemoveFeature { target: FeaturePath, cascade: Cascade },
    RenameSymbol { symbol: SymbolPath, to: Ident },          // writes #[was(original)]
    AddCheck { target: FeaturePath, predicate: IngotExpr, severity: Severity, name: Ident },
    SetMaterial { part: FeaturePath, material: MaterialRef },
    AddDependency { package: PackageName, version: VersionReq },
    CreateFile { path: SourcePath, contents: String },
    DeleteFile { path: SourcePath, expected: Sha256 },
}

pub enum ParamValue { Expr(IngotExpr), FromRef(ValueRef) }   // FromRef cites an untrusted value by handle
```

`EditsApplied` returns the new `ChangeId`, any rebase, the formatted `SourcePatch`es, diagnostics, a semantic diff summary and usage.

**Decision D-AGT-4:** Structured edits are a convenience layer that lowers to Ingot source patches; the formatter normalizes the touched regions, and the response returns the patch.
*Why:* one model with three editors (people, agents, the UI), so reviewers and agents read the same Ingot whatever produced it.
*Rejected:* edits on geometry or on an opaque feature tree, since nothing exists only outside Ingot.

Compile errors fail with `edit/introduces_errors` unless `allow_errors` is set on the agent's own branch. Stale patches fail with `edit/patch_mismatch`, and edits outside the write set with `edit/write_set_violation`.

**Decision D-AGT-5:** Concurrency control is optimistic: every mutating call names its base Change, and on a stale base the server rebases, and says so, only when `repo`'s semantic merge finds no overlapping file, feature, parameter or entity.
*Why:* explicit over magic; an agent needs to know that its view was stale.
*Rejected:* pessimistic locks, which deadlock and are abandoned by crashed agents; silent rebase, which hides semantic interference.

A call, a Proposal merge and a swarm's parent merge are each one Change. On a live branch (phase 2), an agent's Change enters the server-sequenced edit log as one batch of patches and rebases like any person's edit.

### Idempotency

MCP 2026-07-28 removed stream resumability, so clients re-issue requests lost with a broken stream [MCP changelog], and a retried mutation must not apply twice.

**Decision D-AGT-6:** Every method that changes state or spends budget requires an idempotency key, a client-generated 128-bit random value, and the server keeps (principal, method, key) with a SHA-256 fingerprint of the canonical arguments and the response for 24 hours.
*Why:* exactly-once effects under routine retries.
*Rejected:* deduplication by argument hash, which merges legitimately repeated calls; transport resumability, which MCP removed.

| Situation | Behaviour |
| --- | --- |
| Same key and fingerprint, completed | The stored response, marked `replayed: true` |
| Same key and fingerprint, running | `request/in_flight` with `retry_after_ms` |
| Same key, different fingerprint | `request/idempotency_mismatch`, naming the original call |
| Key older than 24 hours | Treated as new, with a notice |

The SDKs generate keys and retry with the same key under capped, jittered exponential backoff.

### Evaluations and streams

Builds, checks, simulations, manufacturing plans, costing and explorations run as Evaluations, each ending in an `EvaluationReport`. Their states map to MCP task states: `queued` and `running` to `working`, `done` to `completed`, and `aborted` to `cancelled` or `failed` [MCP Tasks].

```rust
pub enum Frame {
    Progress { fraction: f32, stage: String },
    Diagnostics(Vec<Diagnostic>),
    Status { node: NodeId, status: ResultStatus },     // base type
    BodyReady { node: NodeId, fidelity: Fidelity, body: ObjectId },
    CheckResult(CheckOutcome),                         // base type, with its verdict
    FieldReady { field: FieldRef, fidelity: Fidelity, budget: BudgetSummary, zones: ZoneSummary },
    ParetoUpdate(ParetoFront),
    Usage(Usage),
    Final(EvaluationReport),
}
```

A long Evaluation returns a task when the client declared the Tasks extension; otherwise the call waits up to `wait_ms` and returns an id for `evaluate.get`. Cancellation is an Abort (contract 7.2), and the final frame lists what completed.

Direct manipulation needs results every frame without a Change per pointer move. `evaluate.subscribe { targets, overrides, ceiling }` opens a result stream under literal overrides keyed by ING's `LiteralSite` (a call site plus an argument slot). `edit.stream` sends override updates to it and ends in exactly one `edit.apply` that writes the final literals, or in a discard. Kiln keys overridden nodes by their overrides, never shares those results, and runs them under the `Drag` priority class on PLT's `Drag` pool lane. UIX's drag preview, MEC's sketch drag and ELX's router use this pair.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Two-crate surface | `api-schema` for types, codec and stubs; `api` for implementations; UIs link `api-schema` only | `cargo xtask check-layers` fails a UI crate that depends on `api` | AGT-O-SDK-1 | 0 |
| Sessions and delegation | Handle bound to principal and issuer; chain from server lineage | `session/expired`, `auth/scope_denied` | AGT-O-POL-1 | 0 (single principal), 1 |
| Delegation grants | Crew token exchange only against a live grant; DPoP or mutual TLS | `auth/no_live_grant` | AGT-O-POL-2 | 2 |
| Local credentials | Device credentials act as `agent:<org>/local/<device>`, `Declared`; human-only methods need a per-call assertion bound to the argument digest | `auth/assertion_required` | AGT-O-INJ-1 | 1 |
| Structured edits | Lower to `SourcePatch`; atomic per call; untrusted values cited by handle | `edit/*` errors with fixes | AGT-O-API-2 | 0 |
| Optimistic concurrency | Exact base; rebase only when disjoint | `edit/stale_base` | AGT-O-API-2 | 0 |
| Idempotency | Keys with fingerprints kept 24 h | `request/idempotency_mismatch` | AGT-O-API-1 | 0 |
| Evaluation streams | Frames over Tasks, polling and SDK streams; identical final results | An Abort lists completed nodes | AGT-O-MCP-1 | 0 |
| Drag streams | `evaluate.subscribe` under `LiteralSite` overrides; `edit.stream` ends in one `edit.apply`; never shared-cached; `Drag` class and lane | `edit/override_site_unknown` | AGT-O-API-2 | 1 |

## Budgets, errors and transports

Agents spend real money, fail often and reach Crucible through hosts it does not control. So every call is priced before it runs, every failure says what to do next, and every transport carries the same catalog.

### Budgets and admission

AGT defines `Budget` and `PriorityClass`, which live in `base`, and PLT adopts `Usage` as its resource record.

```rust
pub struct Budget {
    pub money: Option<Money>,            // base Money { amount: Decimal, currency }
    pub core_seconds: Option<u64>,
    pub gpu_seconds: Option<u64>,
    pub model_tokens: Option<u64>,       // measured calls only
    pub wall_clock: Option<Duration>,
    pub max_evaluations: Option<u32>,
}

pub struct Usage {
    pub core_seconds: u64, pub gpu_seconds: Option<u64>, // None when a shared GPU was unattributed
    pub memory_gb_seconds: u64, pub cas_bytes_written: u64,
    pub model_input_tokens: u64, pub model_output_tokens: u64, pub cost: Money,
    pub declared_tokens: Option<u64>,    // host-reported, never enforced
}
```

Budgets nest from organization to session. The default ceilings are 25 USD per session, 200 USD per Proposal tree and 1,000 USD per day, and raising one is audited.

**Decision D-AGT-29:** Admission reserves the priced upper bound of each Evaluation's work, never a mean, and long Ops run under a deterministic work budget with safe points.
*Why:* solves, certified geometry and Wasm components vary in cost by orders of magnitude at one input size, so a mean admits work that cannot finish.
*Rejected:* regression estimates as reservations; caps only between Ops, which an unbounded factorization overruns.

An Op estimated above 10 core-seconds gets a work budget from the remaining money and reaches a safe point every 10 core-seconds; exhaustion aborts it at its last checkpoint. The work budget never enters a `NodeKey`: an Op completes with its usual value or aborts and writes nothing. GPU seconds come from timestamp queries on compute-only submissions. A failed reservation returns `budget/exceeded` with cheaper options, such as a lower fidelity. A session is warned at 80% of a cap, and spending three times the role's median raises an alert.

| Method kind | Default sustained rate | Burst |
| --- | --- | --- |
| Read, and Inspect except renders | 50 per second | 200 |
| `inspect.render`, `inspect.section`, `inspect.ask_render` | 4 concurrent | None: concurrency-bound |
| Edit (`edit.stream` updates count once per second) | 10 per second | 30 |
| Starting Evaluations | 5 per second | 20 |
| Propose | 1 per second | 10 |
| `act.prepare` | 10 per hour | None: hourly |

Limits apply per principal at the gateway (HTTP 429 or `limit/rate` with a retry delay). Responses default to concise detail; a concise response uses about a third of the tokens of a detailed one [Anthropic writing tools]. Results above 20,000 tokens are truncated with a cursor, below Claude Code's 25,000-token limit for tool results [Anthropic writing tools].

### Priority classes

Kiln owns node scheduling; this tab owns admission and accounting. Every Evaluation carries a `PriorityClass`, and each class runs on one of PLT's pool lanes:

| Class | Used by | Preempted by | Pool lane |
| --- | --- | --- | --- |
| `Drag` | Drags, edit streams and per-pointer tools such as the router | Nothing | `Drag` |
| `Foreground` | A session where a person waits for a result | `Drag`, at node boundaries | `Foreground` |
| `Agent` | Agent sessions | `Drag` and `Foreground`, at node boundaries | `Background` |
| `Ci` | Proposal CI and merge queues | The classes above | `Background` |
| `Batch` | Explorations and benchmarks | All; resumes from cached nodes | `Background` |

Within a class, admission shares capacity by Dominant Resource Fairness, which equalizes each principal's largest share of any resource [Ghodsi et al. 2011]. The word "interactive" names only a fidelity, never a class or a lane.

### Errors as guidance

```rust
pub struct ApiError {
    pub code: ErrorCode,                 // "<family>/<code>", e.g. "edit/stale_base"
    pub r#type: Uri,                     // crucible://errors/edit/stale_base
    pub title: String,
    pub detail: String,                  // external strings only as handles
    pub status: u16,
    pub instance: Uri,                   // this occurrence's audit entry
    pub retry: Retry,                    // Never | After(ms) | AfterChange
    pub fixes: Vec<SuggestedFix>,        // ApplyEdits | Call | Read | AskHuman, most likely first
    pub context: CanonicalJson,          // schema in the error catalog
}
```

**Decision D-AGT-7:** Every failure an agent meets renders as `<family>/<code>`, and `api` returns it as an `ApiError` shaped like RFC 9457 Problem Details, with typed context and ordered fixes, as an MCP tool execution error.
*Why:* RFC 9457 is the standard format [RFC 9457], models self-correct from tool execution errors [MCP tools], one rendering means an agent learns one scheme, and dotted codes read as method names.
*Rejected:* free-text errors; JSON-RPC protocol errors, from which models recover poorly; method-shaped codes; a separate numeric scheme per tab.

One rendering covers `api` errors, Ingot diagnostics (`ing/3001`, lints as `ing/l-fragile-selector`) and every typed `Failure` variant (`<owner family>/<snake_case>`), in a namespace apart from method names. AGT keeps the family registry ([Reference](#error-families)), which gives each family one owner. Diagnostics and `ResolveError`s arrive in `context` with their own fixes. A fix from third-party code carries `data_untrusted` and may not touch dependencies, checks, tolerances, policy or protected paths. An error never names a confidentiality scope or control the caller does not satisfy: it shows an opaque per-tenant id and the text `restricted`, as KLN does everywhere.

### SDKs and WIT

The Rust types in `api-schema` are the single source of truth. A build step emits JSON Schema 2020-12 and generates the MCP tools, the WIT package `crucible:api` and the SDKs, with byte-identical canonical JSON through each. Rust ships in phase 0, Python in phase 1 and TypeScript in phase 2 (contract 13.2).

`crucible:api` serves UIX's `panel` world and ECO's tool and connector worlds, never evaluation worlds. It has one interface per group, each function returning `result<T, api-error>`, and stays at `@0.1.0` until it freezes after contract 13.1's name clearance. WIT types cannot be recursive [WIT specification], so tree-shaped values cross as flat lists: a scene graph is a pre-order list of nodes with parents by index, and `ApiError.context` is canonical JSON text. Calls run under the session's grant narrowed by the component's own grant, and untrusted strings arrive as handles.

### Transports

`apps/mcp` serves the catalog over stdio and Streamable HTTP on the official Rust SDK, `rmcp`, which implements MCP 2026-07-28 and 2025-11-25 [MCP Rust SDK]. MCP 2026-07-28 removes protocol sessions, so each request carries its version and capabilities and stateful servers mint explicit handles [MCP changelog]. It also adds Multi Round-Trip Requests (MRTR, a request that returns for more input and resumes), moves Tasks into an extension, and deprecates Roots, Sampling and Logging.

**Decision D-AGT-2:** Crucible targets MCP 2026-07-28 with the Tasks and Skills extensions and serves 2025-11-25 for twelve months after phase 1; it needs neither extension, since clients can poll `evaluate.get` and read skills as resources.
*Why:* stateless requests scale without sticky sessions, deprecations get at least twelve months, and host support for extensions is outside Crucible's control.
*Rejected:* a custom protocol with no host ecosystem; building on 2025-11-25, which needs session affinity; requiring the extensions.

The element-by-element mapping, header rules and request-state sealing are in [Reference](#mcp-profile). Hosts must treat tool annotations and skill content as untrusted [MCP Skills], so trust in approved role skills binds only the hosted crew. Even so, `skills/list` and `skills/get` serve every host only std roles and roles whose version and digest the organization's `policy:admin` approved.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Admission and metering | Priced upper-bound reservations; safe points every 10 core-seconds | `budget/exceeded`; a budget Abort keeps the checkpoint | AGT-O-BUD-1 | 1 |
| Rate limits | Per principal at the gateway | `limit/rate` | AGT-O-BUD-1 | 0 |
| Priority classes | `Drag`, `Foreground`, `Agent`, `Ci`, `Batch` on PLT's lanes; preemption at node boundaries (KLN); Dominant Resource Fairness within a class | None: admission always assigns a class | AGT-O-BUD-1 | 0 |
| Errors | One `<family>/<code>` rendering; RFC 9457 shape; typed context; ordered fixes; restricted names hidden | Third-party fixes labelled and restricted | AGT-O-MCP-1 | 0 |
| SDKs | Generated from one schema | Schema drift fails the build | AGT-O-SDK-1 | 0 (Rust), 1 (Python), 2 (TypeScript) |
| WIT package `crucible:api` | One interface per group, generated from the Rust types, no recursive types; `@0.1.0` until the freeze | A version mismatch refuses instantiation | AGT-O-SDK-1 | 1 |
| MCP server | 2026-07-28; Tasks and Skills used, neither required; 2025-11-25 for twelve months after phase 1 | An unsupported version returns the supported list | AGT-O-MCP-1 | 0 |
| Skills serving | `skills/list`, `skills/get` and manifests in `apps/mcp`; std and organization-approved roles only | A manifest mismatch refuses the skill | AGT-O-MCP-1 | 1 |

## Observation

An agent cannot glance at a screen, so Crucible gives it five channels that answer from the Kiln results a person sees. They are a scene graph, geometry queries, Snapshots, descriptions and semantic diffs, and every number carries its error bound. A text-only model receives the same facts as a vision model.

### Scene graph and geometry queries

`inspect.scene` returns the evaluated product of one Change as a typed tree, never from UI state. A `SceneNode` carries its instance path (`gearbox/input_shaft[1]`), kind, Item, producing feature and source span, placement, material and representation. It adds bounds and mass properties with `ErrorBound`s, verdict counts, Fields and children. Identical siblings collapse with a count, and a failed build returns a partial graph.

Agents point at geometry the way Ingot does, through queries over provenance and roles:

- `inspect.query` evaluates a query such as `part.faces(normal: +z, area: 100mm2..)` and returns entities with `Merged`, `Partial`, `FragileAnchor` or `NearTie` notes, or a typed `ResolveError`.
- `inspect.entity` returns type, size, adjacency and provenance from `HistoryRecord`s.
- `inspect.measure` returns a `Quantity` with an `ErrorBound` and witness points.
- `inspect.suggest_query` turns entities picked from a Snapshot into queries that keep resolving to them.

**Decision D-AGT-8:** Agents select geometry only through `Query` expressions and `EntityId`s, and `inspect.suggest_query` ranks candidates by ANV's sampled stability analysis, reporting `RankSwap { at }` with its sample; the score is sampled stability, never a guarantee.
*Why:* resolution certifies only the evaluated configuration, while a rank selector such as "longest edge" can flip inside a parameter range like the bracket's `width`.
*Rejected:* indices or screen coordinates; the first query that resolves; a fixed ±10% sampling alone; sampled scores presented as guarantees.

The score is the fraction of sampled configurations that resolve to the same lineage. Agents submit queries scoring 1.0 unless the rationale states a deviation, and the CI report carries protected-branch stability results.

### Snapshots and Field overlays

```rust
pub struct RenderRequest {
    pub change: ChangeRef,
    pub targets: Option<Vec<InstancePath>>,
    pub views: Views,                    // Named(Iso | Front | Top | Right) | Grid4 | Custom(Camera)
    pub style: DisplayStyle,             // UIX's: Shaded, HiddenLine, Wireframe, XRay …
    pub appearance: Appearance,          // Neutral (default for agents) | Imported
    pub overlay: Option<FieldOverlay>,   // Field, fixed range, colour map, isolines, extrema
    pub marks: Marks,                    // None | Entities { kinds, max ≤ 64 } | Explicit(Vec<EntityId>)
    pub section: Option<Plane>,
    pub size: (u16, u16),                // default 1024 x 768; max 2048 x 2048
    pub profile: RenderProfile,          // UIX: locale, theme, display units, font pins, renderer version
}

pub struct Rendered {
    pub snapshot: ObjectId,              // PNG
    pub marks: Vec<Mark>,                // label "7" -> EntityId, kind, size, normal
    pub legend: Option<Legend>,          // unit, range, ticks, validity zones
    pub extrema: Vec<Probe>,             // value with interpolation error
    pub renderer: RendererIdentity,      // image digest, driver; class Unverified
    pub instruction_capable: bool,
    pub visible_summary: Description,    // from typed facts; untrusted names as handles
}
```

The server resolves each request to a UIX `ViewState`, so a Snapshot is a `ViewState` under a `RenderProfile` (contract 2). Marks follow Set-of-Mark prompting [Yang et al. 2023], and each label maps to an `EntityId`, so "fillet the edges marked 3 and 7" resolves exactly. `Grid4` returns four views in one image, as Zookeeper's self-review does.

**Decision D-AGT-9:** `inspect.render` dispatches to `apps/headless-render`, which links UIX's renderer; Snapshots key on a `RenderProfile`, return marks and legends as data, stay `Unverified` and outside every `NodeKey`, and compare by ꟻLIP.
*Why:* software rasterizers generate code per host CPU, so bytes differ across the canonical platform class [Mesa llvmpipe]; profiles change legends; and core crates never link apps.
*Rejected:* canonical CPU renders; images without structured side data; rendering inside `api`.

Byte identity holds only on one pinned CI renderer image, and elsewhere thresholds on ꟻLIP, a perceptual image difference, apply [NVIDIA FLIP]. `api` depends on neither the renderer nor the service. Proposals and benchmarks use the review profile (`en`, SI with millimetres, light theme), and Proposal Snapshots are stored once as Assets, so every reviewer sees the same bytes.

**Decision D-AGT-26:** A Snapshot or section SVG is instruction-capable when its appearance is imported or its visible text, or geometry made from text, derives from an untrusted `ExternalText` value; a clean context asks about one only through `inspect.ask_render`.
*Why:* embossed letters, part names, notes and textures can carry instructions, and answers computed from attacker-chosen pixels can still steer an edit.
*Rejected:* trusting every Snapshot; tainting every Snapshot of an assembly with a merged supplier part; trusted `ask_render` answers.

`inspect.ask_render` is a quarantined vision call on a versioned `std::agents` template, and its `ValueRef` answers set `data_untrusted`. The scene graph, measurements and descriptions stay non-tainting, because every string they take from an `ExternalText` value is a handle.

### Sections and descriptions

`inspect.section` returns curves with the cut plane's `ErrorBound`, an SVG hatched per material and an optional Field overlay. An empty cut returns the nearest offset that meets material.

`inspect.describe` renders typed facts through templates, without a model. It returns `text`, `facts` (each number with its source and bound) and a `detail` level of `Brief` (80 words), `Standard` (400) or `Full`; the walkthrough above shows the bracket's brief description.

**Decision D-AGT-10:** Canonical descriptions come from typed facts and templates with no model text, and a third-party template's phrasing is an `ExternalText` handle.
*Why:* descriptions feed reviews and benchmarks, so every number must trace to a fact, and publisher verification establishes identity, not safe text.
*Rejected:* model-written canonical descriptions; trusting verified publishers' templates.

Only the canonical form is stored, diffed and reviewed, and std and `crucible::` phrasing is trusted.

### Semantic diffs

`compare.diff` explains what changed between two Changes, at seven levels:

| Level | Content |
| --- | --- |
| Source | Formatted Ingot text diff, free text as handles |
| Features | Features added, removed or moved; parameters old → new, with units |
| Checks | Verdict and margin changes; checks added, removed or loosened; `#[waive]` requests |
| Geometry | Volume added and removed; Hausdorff deviation with an `ErrorBound` (Anvil) |
| Metrics | Mass, cost, regularized peaks, cycle time and declared objectives, with intervals |
| BOM | Lines added or removed, quantity changes, new catalog parts |
| Policy | Checks, tolerances, oracle references, protected paths, lockfile pins, recipient records |

The overlay shows added and removed material in a colour-blind-safe pair over ghosted geometry. A policy-level change sets `policy_sensitive: true` for risk classification.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Scene graph and measurements | Typed tree from Kiln results; `Quantity` with `ErrorBound` and witnesses | A partial graph with diagnostics | AGT-O-OBS-1 | 1 |
| Geometry queries | `Query` and `EntityId` only; `NearTie` and other notes surfaced | `query/resolve_failed` with ranked candidates | AGT-O-OBS-3 | 1 |
| Query robustness ranking | ANV's sampled stability analysis; `RankSwap` with its sample; never a guarantee | `query/no_robust_candidate` | AGT-O-OBS-3 | 1 |
| Snapshots and overlays | `apps/headless-render`; `RenderProfile` in the key; `Unverified` class; ꟻLIP comparison; legends as data | `render/too_many_marks` | AGT-O-OBS-1 | 1 |
| Instruction-capable images | Neutral appearance; quarantined `inspect.ask_render` answering with `ValueRef`s | Reading one directly sets `instruction_tainted` | AGT-O-INJ-1 | 2 |
| Sections | Curves with bounds, SVG, overlay | `inspect/empty_section` with the nearest offset | AGT-O-OBS-1 | 1 |
| Descriptions | Template-generated; every number a fact; third-party phrasing as handles | `build/failed` describes what built | AGT-O-OBS-2 | 0 (source facts), 1 (evaluated facts) |
| Semantic diffs | Seven levels; `policy_sensitive` flag | `compare/unrelated`, flagged | AGT-O-RISK-1 | 1 |

## Roles

A role turns "an agent" into a colleague with a job description: what it may touch, what it must prove before it hands work over, and what it may never read.

A role is a `Role` record in a package: scopes, a write-set rule, an external-text policy (never, or extracts), exit checks, outputs and model requirements. Its skill lives at `skill://crucible/<role>/SKILL.md` with a manifest digest. The crew is the set of roles in the open-source `std::agents`, and anyone can publish another.

**Decision D-AGT-11:** Roles are data plus instructions in an open package, and their exit criteria are checks in `std::agents::exit`, which CI evaluates over the typed `std::agents::proposal` view.
*Why:* "no privileged code" applies to agents too, and exit criteria must be machine-checkable to be oracles.
*Rejected:* roles hard-coded in the runtime, which are privileged and opaque; prose-only exit criteria, which nothing enforces.

A role skill changes only through a reviewed, benchmarked Proposal. The hosted crew loads another publisher's role only after `policy:admin` approves its version and digest.

### Scopes

Scopes are the units of permission in grants, tokens and roles. There is no wildcard, and hosts request more scopes by step-up [MCP security practices].

| Scope | Grants |
| --- | --- |
| `design:read` | Read, Inspect and Compare methods, except `read.external_text`, `read.value` and `read.audit` |
| `external:read` | `read.external_text` and `read.value`, as quarantined extraction allows |
| `design:edit` | Edit methods on the session's branch, within its write set |
| `eval:build`, `eval:simulate[:fidelity]`, `eval:manufacture`, `eval:cost`, `eval:explore` | The matching Evaluate methods, simulation up to the stated fidelity |
| `propose:author`, `propose:review`, `propose:merge`, `propose:plan` | Authoring; review outside one's own lineage; merge under policy; plans and child sessions |
| `act:<kind>` | `act.prepare` and `act.commit` for one Act kind; the commit waits for an assigned human |
| `audit:read` | `read.audit` |
| `policy:admin` | Cedar authorization policies, branch protection, clearances, recipients and auto-merge; people only, never by token exchange |

### Role catalog

Every role holds `design:read` and `propose:author`. The verifier and the DFM (design for manufacturing) reviewer add `propose:review`, and the planner adds `propose:plan` and `propose:merge` on its integration branch.

| Role | Writes | External text | Exit checks (`std::agents::exit`) | Acts it may prepare | Phase |
| --- | --- | --- | --- | --- | --- |
| Planner | Its integration branch, only by merging children | Never | `plan_is_acyclic`, `parallel_write_sets_disjoint`, `every_item_has_acceptance_checks`, `budgets_within_parent`, `parent_ci_green`, `verifier_approved` | None | 2 |
| Requirements analyst | `requirements/**` | Extracts | `every_requirement_has_id_and_source`, `every_requirement_has_verification_method`, `quantities_typed`, `open_questions_listed` | None | 2 |
| Concept designer | Own concept branches | Never | `concepts_distinct`, `each_concept_builds`, `requirements_coverage_reported` | None | 2 |
| Detail designer | Work-item write set | Never | `builds_at_declared_fidelity`, `all_checks_meet_gate`, `no_new_fragile_queries`, `tolerances_on_mating_features`, `no_allow_errors_changes` | None | 1 |
| Simulation engineer | `studies/**` and checks on results | Never | `convergence_demonstrated`, `results_within_validity_envelope`, `loads_trace_to_requirements`, `signoff_fidelity_for_release_checks`, `verification_case_passed` | None | 1 |
| DFM reviewer | None; findings carry fixes | Never | `every_finding_anchored`, `every_blocker_has_fix_or_rationale`, `rules_version_recorded` | None | 2 |
| CAM programmer | `mfg/cam/**` | Extracts (tool data) | `no_collisions`, `no_gouges`, `stock_removed_within_tolerance`, `tools_in_library`, `feeds_within_tool_limits`, `posted_for_machine_class` | `send_to_machine`, `store_machine_job` | 2 |
| Cost engineer | `cost/**` and cost-reduction branches | Extracts (quotes) | `every_bom_line_priced_or_flagged`, `prices_have_source_and_date`, `totals_have_intervals` | `request_quote` | 2 |
| Drawing and MBD author | Drawing source and PMI | Never | `every_feature_of_size_toleranced`, `datum_reference_frames_complete`, `annotations_reference_live_entities`, `pmi_semantic_in_ap242_export` | None | 2 |
| Catalog librarian | Catalog package repository | Extracts | `key_dimensions_match_datasheet`, `units_typed`, `geometry_licence_recorded`, `provenance_recorded` | `publish_package` | 2 |
| Documentation writer | `docs/**` except drawings | Never | `every_number_cites_a_fact`, `facts_current_at_head`, `snapshots_within_threshold` | None | 2 |
| Independent verifier | Own scratch and counter-proposal branches | Never | `attack_catalog_covered`, `findings_reproducible`, `mutation_score_reported` | None | 1 |

Phase 1 ships contract 13.2's three roles (detail designer, simulation engineer and verifier) to external MCP hosts; the CAM programmer arrives with CAM in phase 2. MBD is model-based definition, a drawing's content carried as semantic PMI (product and manufacturing information) on the 3D model. A value a role cannot source, such as a tolerance or a price, becomes a finding for a human, never an invention.

Reviewers never edit what they review, and catalog librarian Proposals always carry `data_untrusted`. A CAM program is offered to a person one strategy at a time, as CloudNC's CAM Assist offers strategies to accept [CloudNC CAM Assist].

### Planner

The planner turns a goal into a validated plan, dispatches work items and assembles the parent Proposal, and never edits design source. It never reads external text, so its actions are fixed before any untrusted data is processed, the Plan-Then-Execute pattern [Beurer-Kellner et al. 2025]. An item that exhausts its attempts gets one re-plan and then goes to the delegating human with its failure history.

### Independent verifier

The verifier runs in a fresh context that shares no session lineage with the author, on another model family where policy requires it. Its typed view holds the requirements, the Ingot IR, the semantic diff, check outcomes, the CI report and the rationale's typed fields, never the author's free text.

Every review attacks uncovered requirements, worst-case tolerance stacks, omitted load cases, material extremes, query fragility, manufacturability and a CI replay in another platform class. Check mutation thins walls by 50%, removes fillets, doubles loads and swaps in the weakest permitted material. A check that survives every mutation is flagged as possibly vacuous, and each finding carries an Ingot test that fails on the head.

**Decision D-AGT-12:** Every agent Proposal faces a verifier that shares no lineage with the author, sees no author free text and runs a fixed attack catalog with check mutation.
*Why:* self-review shares the author's blind spots, the author's text is an injection channel, and Crucible cannot see one host play both roles.
*Rejected:* self-verification; render questions alone, since CADCodeVerify's improvement in point-cloud distance [Alrashedy et al. 2024] misses checks that cannot fail; server lineage alone.

The review is `Attested` only under a different delegating human, in the hosted crew or behind the model gateway; a `Declared` review needs a human approval beside it. Mutation covers the changed Parts and the checks their dependency closure reaches. Beyond the verifier's budget, a fixed hash rule samples them, and the report states the count.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Role packages | `Role` records with skills and manifest digests in `std::agents` | An unapproved manifest refuses the role in the hosted crew | AGT-O-MCP-1 | 1 |
| Scopes | No wildcard; incremental step-up; `policy:admin` people only | `auth/scope_denied` | AGT-O-POL-1 | 1 |
| Exit checks | `std::agents::exit` over the typed Proposal view | `propose/preconditions_failed` | AGT-O-BENCH-1 | 1 |
| Phase 1 roles | Detail designer, simulation engineer, verifier | `session/role_unavailable` | AGT-O-BENCH-1 | 1 |
| Further roles | The nine others in the catalog | `session/role_unavailable` | AGT-O-BENCH-1 | 2 |
| Independent verifier | Typed view; attack catalog; scoped mutation; `Attested` or `Declared` | Merge blocked until a verifier review exists at the head | AGT-O-VER-1 | 1 |

## Proposals and review

A reviewer's time is the scarcest resource around an agent, so a Proposal arrives proven where proof is mechanical and classed by risk where judgement is needed.

### The Proposal object

A Proposal is a branch plus rationale plus CI report, stored by `repo`.

```rust
pub struct Proposal {
    pub id: ProposalId,
    pub source: BranchName,
    pub target: BranchName,
    pub base: ChangeId,
    pub head: ChangeId,
    pub rationale: Rationale,            // typed fields plus a free-text summary
    pub author: PrincipalId,
    pub delegation: Vec<PrincipalId>,    // index 0 = delegating human, last = current actor
    pub parent: Option<ProposalId>,
    pub plan: Option<Plan>,
    pub ci: Option<CiReport>,            // written only by service:ci
    pub snapshots: Vec<ObjectId>,        // server-generated at head, review profile
    pub risk: RiskAssessment,            // class and the diff items that set it
    pub labels: Labels,                  // join of every authoring context's label
    pub reviews: Vec<ReviewVerdict>,
    pub state: ProposalState,            // Draft | Open { ready } | Merged | Withdrawn | Superseded
    pub usage: Usage,
}
```

`Rationale` holds a summary, requirement ids, design choices with the facts that support them (check outcomes, Field statistics, measurements), deviations and limitations. Before a non-draft `propose.create`, the server checks five preconditions:

1. The head builds at each target's declared fidelity.
2. Every check meets the gate predicate (contract 5.6); a `#[waive]` request counts only with a matching Waiver record, which no agent signs.
3. Snapshots exist at the head: a `Grid4` of each changed Part or Assembly, a geometry-overlay diff and an overlay per changed study.
4. The rationale has a summary and, where requirements exist, a requirement link.
5. Every Change on the branch carries complete, signed provenance.

A failure returns `propose/preconditions_failed` with fixes. Drafts skip the first three and cannot be merged.

`service:ci` writes the `CiReport` on untrusted-evaluation workers (contract 7.8), and `evaluate.ci` shows agents the same report in advance. The report names the Change and the lockfile digest, which pins every policy package and Evidence record the checks read. It holds each CI Evaluation's `EvaluationReport`: outcomes per platform class, deltas, zone flags, query stability, oracle integrity and usage. Trusted builders recompute what a release needs after the merge.

### Risk classes

The risk class decides who must look at a Proposal, so the server computes it, never a model.

| Class | Meaning | Examples |
| --- | --- | --- |
| R0 | No semantic change | Formatting and comments with an identical IR hash; regenerated Snapshots |
| R1 | Contained design change | Parameters within declared ranges on unreleased designs; no check, tolerance, BOM or dependency change; no margin below 90% of its target-head value; every authoring context clean |
| R2 | Ordinary design change | New features, checks, studies or materials; BOM changes; dependency updates that keep behaviour versions; any R1-shaped change from a `data_untrusted` context, every `Declared` host included |
| R3 | Sensitive change | Checks or tolerances loosened; `#[waive]` requests; oracle references; protected paths; behaviour-version bumps; change orders; any change from an `instruction_tainted` context |
| R4 | Critical | Changes that feed an Act kind (a release candidate, a posted program, files bound for a supplier); policy repository changes; recipient records |

**Decision D-AGT-16:** The risk class is a deterministic function of the semantic diff, the target and every authoring context's integrity flags, with floors of R3 for loosening, waiver requests and tainted content and R2 for untrusted content.
*Why:* loosening a check is the cheapest reward hack, and untrusted typed values can steer an edit without any text.
*Rejected:* model-assessed risk; one class for all agent work, which breeds review fatigue; calling an unseen host's context clean.

`instruction_tainted` content sets the R3 floor, and `data_untrusted` content, every `Declared` host included, sets the R2 floor. Merging clears integrity on typed values, never free text (contract 5.3). A merged supplier STEP file therefore contributes trusted geometry and numbers, while its part names stay `ExternalText` values that travel as handles. An R1-shaped edit to an assembly that contains a merged supplier part stays R1, because no node downstream inherits the names' integrity.

### Human review and separation of duties

For agent Proposals, UIX's Proposal view adds provenance, the risk class and its reasons, integrity flags with their sources, the verifier's report and the canonical description. Findings anchor to `EntityId`s, feature paths or source spans and return to the author as typed input.

- A merge into a protected branch needs the merge approvals its branch rule requires, from reviewers outside the authoring and delegation chain, each with a fresh approval credential bound to the call (contract 5.4).
- Into an unprotected branch, the delegating human may merge R0 to R2; R3 and R4 always need a person outside the chain.
- Agent reviews never count toward a human approval requirement.
- Change orders follow KLN's review routing from phase 2 ([KLN, review routes](05-kiln-repo-plm.md#review-routes-and-delegation)). A route has ordered stages of roles with a quorum, conditions that add stages, and delegation during absence that never names an agent. The Proposal view shows the route's progress.

### Auto-merge

Auto-merge is a repository policy, off by default, changed only by two people under the signature table (contract 5.4).

```rust
pub struct AutoMergePolicy {
    pub enabled: bool,                   // default false
    pub classes: Vec<RiskClass>,         // R0 and R1 only; others rejected at validation
    pub targets: Vec<BranchPattern>,     // never release branches or tags
    pub max_geometry_deviation: Length,  // e.g. 0.5mm Hausdorff
    pub max_cost_increase: Ratio,        // e.g. 1%
    pub quiet_period: Duration,          // default 10 min; any watcher may veto
    pub max_per_day: u32,                // default 20 per repository
}
```

**Decision D-AGT-17:** Auto-merge applies only to R0 and R1 Proposals from clean contexts, with an `Attested` verifier review, CI meeting the gate in two platform classes and an unvetoed quiet period.
*Why:* low-risk changes should not queue behind people, behaviour changes need accountability, and a host context Crucible cannot see is not clean.
*Rejected:* auto-merge on "all checks pass", since checks can be incomplete; never auto-merging, which breeds review fatigue; auto-merge for external hosts.

Only hosted-crew and gateway-attested contexts with no outside tools can be clean, and R2 and above always need a person. `service:merge` performs auto-merges, never the author, and records the policy version. An agent freeze stops auto-merge, new agent sessions and agent writes within 5 seconds (target).

### Provenance

The API server writes and signs a record for every Change, so an agent cannot forge its own history.

```rust
pub struct ChangeProvenance {
    pub change: ChangeId,
    pub principal: PrincipalId,
    pub delegation: Vec<PrincipalId>,
    pub session: SessionId,
    pub role: Option<(RoleRef, Sha256)>,         // role version and skill manifest digest
    pub endpoint: Option<EndpointRecord>,        // the model endpoint, when attested
    pub assurance: Assurance,                    // Attested (crew or gateway) | Declared
    pub instructions: Sha256,                    // goal, work item, skill, system prompt
    pub client: ClientInfo,                      // client identity; tool inventory
    pub context: Labels,
    pub inputs: Vec<ReadRecord>,                 // digests of what the context read
    pub transcript: Option<ObjectId>,            // hosted crew always; other hosts if uploaded
}
```

Each record is an in-toto Statement v1 with the Change digest as its subject [in-toto Statement], signed by the deployment's provenance key. The model is attested only when the crew or the gateway made the call, and is otherwise `Declared`. Instructions and transcripts keep the context's label and their own retention.

### Reversibility

| Effect | Undone by |
| --- | --- |
| A Change on an agent's own branch | `edit.reset_branch`, `edit.undo` or `edit.revert` |
| A merge, swarm result or auto-merge | `edit.revert` as a forward Change in a Proposal; a daily digest lists auto-merges |
| A release | Not undoable; superseded by a change order and a new release |
| A compensable or revocable Act | Cancellation or revocation, recorded as a new Act |
| An irreversible Act | Not undoable, hence approval of the exact plan |

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Proposal records | Fields above; labels joined from authoring contexts | `propose/closed` | AGT-O-RISK-1 | 1 |
| Preconditions | Build, gate predicate on every check, Snapshots, rationale, provenance | `propose/preconditions_failed` with fixes | AGT-O-RISK-1 | 1 |
| CI report | `service:ci` on untrusted-evaluation workers; per-Proposal namespace; lockfile digest; one `EvaluationReport` per Evaluation | `propose/ci_unwritable` for any other writer | AGT-O-RISK-1 | 1 |
| Risk classes | Deterministic from diff, target and integrity flags; `Declared` hosts at least R2 | None: every Proposal gets a class | AGT-O-RISK-1 | 1 |
| Separation of duties | Chain from server lineage; protected merges and R3 or R4 need people outside it | `propose/self_review_forbidden` | AGT-O-POL-1 | 1 |
| Review routing for change orders | KLN's stages, quorum, conditions and delegation applied to `propose.change_order`; never delegated to an agent | `propose/route_incomplete` | AGT-O-POL-1 | 2 |
| Auto-merge | R0 and R1 from clean attested contexts; `Attested` verifier; two classes; quiet period | `propose/policy_unsatisfied` | AGT-O-RISK-1 | 2 |
| Agent freeze | All agent writes stop within 5 s (target) | None: a freeze cannot be refused | AGT-O-POL-1 | 1 |
| Provenance | Signed in-toto statements for every Change | An unsigned Change is refused | AGT-O-PROV-1 | 1 |

## Swarms and exploration

Some tasks split into independent pieces, such as a gearbox's shafts and housing, or one part replaced across thirty assemblies. A swarm runs those pieces in parallel and still delivers one reviewed result.

A swarm is a tree of Proposals: a plan, child Proposals on workers' branches, a merge queue and a verifier before the target.

### When to use a swarm

Multi-agent systems use about 15 times the tokens of a chat and suit heavily parallel work, while coding parallelizes less well [Anthropic multi-agent research]. Design work is closer to coding.

**Decision D-AGT-13:** The default is a single agent, and a swarm starts only when a validated plan has at least two parallel items, with at most 8 workers per Proposal tree and a delegation depth of 2.
*Why:* cost outgrows benefit when work is not parallel, and Anthropic saw 50 subagents spawned for simple queries.
*Rejected:* always-on swarms, for their cost and merge churn; unbounded recursive delegation, for its cost and blurred accountability.

The planner and the verifier may use the strongest qualified model endpoint and workers a cheaper one. On Anthropic's internal research evaluation, an Opus 4 lead with Sonnet 4 subagents outperformed a single Opus 4 agent by 90.2% [Anthropic multi-agent research]; golden tasks measure whether the same split helps design work.

### Plans and work items

```rust
pub struct WorkItem {
    pub id: WorkItemId,
    pub role: RoleRef,
    pub requirements: Vec<RequirementId>,
    pub write_set: WriteSet,
    pub depends_on: Vec<WorkItemId>,
    pub acceptance: Vec<CheckRef>,       // must exist, or be added by the item, and pass
    pub held_out: Option<HeldOutRef>,    // graded by service:ci; never readable by the worker
    pub budget: Budget,
    pub max_attempts: u8,                // default 3
    pub state: WorkItemState,            // Pending | Leased { session, attempt, until } | Proposed | Merged | Failed
}
```

A `Plan` holds the goal, the items, an integration branch, a budget carved from the parent Proposal's and `max_parallel` (default 8). `propose.plan` checks acyclicity, disjoint concurrent write sets, acceptance checks, budgets and qualified endpoints, or fails with `plan/invalid`. A valid plan creates the integration branch.

Contract 13.2's build-program work item is this record: its crate maps to the write set, its capability row to a requirement, its oracle ids to acceptance and its held-out split to `held_out`. The build program's taint rule applies unchanged. A context that read third-party source, a web page or a paper is `instruction_tainted`, writes only its own branches, and needs the founder's Approval to change protected trees.

### Execution

[[DIAGRAM diagrams/09-agents-swarm-flow.jsx: swarm flow · planner, parallel workers, merge queue, two verifiers]]

Read the diagram top to bottom, then along the bottom row: solid arrows carry changes, dashed arrows send Evaluations to Kiln, and the left column shows each level's budget.

1. **Dispatch.** Each ready item is leased, up to `max_parallel`, to a child session on a branch forked from the integration head.
2. **Work.** The worker reads, edits, builds, checks and inspects, then proposes into the integration branch.
3. **Light verification.** A verifier checks each child for uncovered requirements, check mutation and query fragility.
4. **Merge queue.** Children merge in dependency order with CI on each result, so the integration head always meets the gate predicate.
5. **Assembly and review.** The parent Proposal targets the real branch, the verifier runs its full catalog, and review follows.

A lease lasts 10 minutes and any call renews it. An expired lease returns the item to `Pending`, and stale writes fail with `session/lease_lost`. Plan state lives on the parent Proposal, so the crew resumes after a restart.

### Coordination without messages

**Decision D-AGT-14:** Agents never message each other directly: plans, work items, Proposals, reviews and anchored comments written through the API are the only medium.
*Why:* coordination stays versioned, audited and visible; spoofed inter-agent messages are a named agentic risk [OWASP agentic top 10]; and agent-to-agent protocol messages are free text outside labels.
*Rejected:* direct messaging, including the A2A protocol; a shared scratch memory, which can be poisoned.

Agents in two organizations cooperate only through export Acts to a shared branch and through standing releases. Another agent's comment arrives as an `ExternalText` handle, so agents exchange facts through typed failure reports, findings with tests and check outcomes.

| Stage | Outcome |
| --- | --- |
| Prevention | Concurrent items have disjoint write sets; overlapping ones run in sequence |
| Semantic conflict | A conflict on a feature, parameter, entity or net returns the item to its worker as typed input |
| Behavioural conflict | Children pass alone but the merge fails a check: a reconcile item gets both diffs and the failing check |
| Alternatives | Competing passing solutions are ranked by the plan's objectives; a tie goes to a person |
| Exhaustion | One re-plan, then the delegating human sees both alternatives with their failure histories |

### Mass changes

Replacing an obsolete part everywhere it is used is routine PLM work. KLN owns the method, `propose.mass_change(from, to, scope)`, and its rule that one change order releases only when every affected repository's Proposal passes ([KLN, where-used](05-kiln-repo-plm.md#where-used)). This tab runs it.

**Decision D-AGT-35:** A mass change runs on the swarm machinery: the planner turns KLN's where-used result into a plan with one work item per repository, each worker's Proposal targets its own repository, and the change order takes the place of the integration branch.
*Why:* plans, leases, per-item CI, verification and resumption after a restart already exist, so a mass change needs no mechanism of its own.
*Rejected:* a dedicated bulk-edit service, which would duplicate the swarm's controls; one Proposal spanning repositories, which no single CI can evaluate.

### Design-space exploration

`evaluate.explore` searches a parametric space for trade-offs through Kiln and Flux. Variants are parameter assignments in a record in the CAS, Crucible's content-addressed store, not branches. A request names variables, objectives with units, constraints (by default every `Error`-severity check), a fidelity ladder, a strategy, a batch size, a budget and a seed.

| Situation | Strategy |
| --- | --- |
| Initial design | Scrambled Sobol sequence of 2(d + 1) points |
| Expensive variants (under about 500 affordable, up to about 50 variables) | Bayesian optimization: qLogNEHVI, or qLogNoisyExpectedImprovement for one objective [Ament et al. 2023]; dimension-scaled lengthscale priors [Hvarfner et al. 2024] |
| Cheap variants or mostly categorical spaces | NSGA-II for two objectives, NSGA-III for more [pymoo algorithms] |
| Several fidelities or separable objectives (phase 3) | Hypervolume knowledge gradient [Daulton et al. 2023] |

**Decision D-AGT-15:** Exploration strategies are Rust in the Wasm component package `std::explore`, with BoTorch and pymoo as references, and rounds are synchronous unless a request opts into non-reproducible asynchronous batches.
*Why:* Python and PyTorch cannot run deterministically in the sandbox, on every OS or in browsers, and reproducible records outweigh asynchronous throughput.
*Rejected:* a BoTorch sidecar, with no browser and no determinism; evolutionary methods only, though each variant costs a Flux solve and Bayesian optimization targets costly functions [BoTorch introduction].

- **Failures** keep their typed errors, and a Gaussian-process classifier weights acquisition by build success.
- **Validity.** `Invalid` or `Extrapolated` results leave the Pareto front by default.
- **Fidelity ladder.** Screening runs at `Interactive` and the top five rerun at `SignOff`; disjoint enclosures flag `fidelity_disagreement`.
- **Determinism.** Seeds are inputs, and Gaussian processes fit by deterministic L-BFGS from fixed Sobol restarts.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Plans and validation | Acyclic, disjoint concurrent write sets, acceptance checks, budgets; held-out grading | `plan/invalid` with fixes | AGT-O-SWARM-1 | 2 |
| Leases and fencing | 10-minute leases; attempt numbers fence stale writers | `session/lease_lost` | AGT-O-SWARM-1 | 2 |
| Merge queue | Children merge in dependency order with CI per merge | Conflicts return to the worker as typed input | AGT-O-SWARM-1 | 2 |
| Mass-change orchestration | KLN's `propose.mass_change` as a plan with one work item per repository under one change order | `propose/mass_change_incomplete` listing failing repositories | AGT-O-SWARM-1 | 3 |
| Exploration | `std::explore`: Sobol, NSGA-II and III, Bayesian optimization; deterministic in synchronous mode | `explore/no_feasible_point`; failures counted | AGT-O-EXP-1 | 2 |
| Multi-fidelity exploration | Hypervolume knowledge gradient | Falls back to single-fidelity search, reported | AGT-O-EXP-1 | 3 |

## Labels and injection defence

Any text an agent reads may be an attacker's instruction, and no model reliably tells the difference. So Crucible decides what an agent may do from whom it acts for and what it has read, never from what the text says.

Prompt injection is unsolved: Meta calls it "a fundamental, unsolved weakness in all LLMs" [Meta Rule of Two], and OWASP ranks it first among LLM risks [OWASP LLM01]. Crucible therefore relies on no model resisting it. Authority comes only from principals and grants, every value carries `Labels`, and the server enforces every boundary. The table maps OWASP's agentic risks [OWASP agentic top 10] to the controls that answer them.

| Threat (OWASP agentic risk) | Primary controls |
| --- | --- |
| Instructions in imports, comments, strings or textures (ASI01) | Four instruction sources; handles; labels; quarantined extraction |
| Misuse of a legitimate method (ASI02) | Scopes, write sets, risk classes, Act approvals |
| Stolen or escalated credentials (ASI03) | Sender-constrained tokens; delegation grants; local credentials act as device agents |
| Malicious servers, skills or packages (ASI04) | Approved skill manifests; signed packages; stdio MCP servers only in PLT's sandbox |
| Code execution (ASI05) | Only Ingot and determinized Wasm components; Proposal CI in single-use microVMs |
| Poisoned memory, spoofed messages (ASI06, ASI07) | No shared agent memory; no direct messaging |
| Cascading failures (ASI08) | Budgets, attempt limits, merge-queue CI, freeze |
| Over-trust by reviewers (ASI09) | Risk classes, verifier reports, server-generated approval pages |
| Rogue agents and exfiltration (ASI10) | Write-down, clearances, three audited exits |

### Instruction authority

**Decision D-AGT-18:** Instruction authority has four sources: the delegating human's goal, approved role skills, first-party documentation from the hermetic builder, and endorsed spans; everything else returns as a handle.
*Why:* provable defences constrain what an agent may do after it reads untrusted input [Beurer-Kellner et al. 2025], and merged comments and agent-written part names have both carried injected text.
*Rejected:* classifiers or spotlighting as primary controls, kept only as signals; trusting verified publishers or protected branches; returning endorsed spans raw without listing them.

Untrusted origins are imported files, supplier, catalog and web content, third-party package text, extraction output and attachments. A string evaluated from an untrusted free-text span is an `ExternalText` value carrying the span's integrity (contract 5.3), so text integrity travels with the value, not with the node that holds it. `api` returns every `ExternalText` value as a handle wherever it appears: scene names, BOM text, check names, quoted diagnostics, CI reports, diffs and description facts. `repo` records each span's integrity as the server witnessed it, and a span returns as a handle when its author is outside the reader's delegation chain or its integrity is untrusted.

A span becomes trusted only through `propose.endorse_text`. One human reader sees it verbatim, with invisible and bidirectional characters highlighted, and signs over its bytes with an approval credential (contract 5.4). Importers keep original names as `external("...")` values, which are never endorsed.

### Context labels and write-down

**Decision D-AGT-24:** Every model context carries the join of the `Labels` of every value returned to it, and every write carries at least that label.
*Why:* a context is a derivation path Kiln never sees, so without its own label it would launder what it read.
*Rejected:* labelling only Kiln derivations; non-tainting typed values; labels per token family or workspace; integrity that blocks writes.

An external host's context is a server-stored (user, client identity) pair that every token family, grant and stdio launch joins, so a reconnecting host never gets a clean label. Write-down compares confidentiality only; the exits compare confidentiality and usage, because a licence restricts where data goes rather than who in the tenant reads it.

The hosted crew's context is its conversation. Reading an `ExternalText` value's content or an instruction-capable image sets `instruction_tainted`, any untrusted value sets `data_untrusted`, and trusted text never taints. A write to a destination with a lower confidentiality label fails with `label/write_down` unless a declassification record names it. Only `session.reset_context`, confirmed by the human with WebAuthn after clearing the host's conversation, resets a label; the reset is audited and shown in provenance.

### Taint and the Rule of Two

Meta's Rule of Two says an agent should hold at most two of three things: untrusted input, access to sensitive data, and the power to change state or communicate [Meta Rule of Two]. Crucible applies it per context:

| Context | Edit own branch | Propose | Merge or auto-merge | Prepare Acts |
| --- | --- | --- | --- | --- |
| Clean (hosted crew or gateway-attested only) | Yes | Yes | Subject to policy | Yes |
| `data_untrusted` | Yes | Yes; at least R2 | No auto-merge | Yes; the plan carries the flag |
| `instruction_tainted` | Yes | Yes; at least R3 | No | Yes; the approval page lists the taint sources |

An `instruction_tainted` context holds all three powers, but narrowly. It changes only its own branches, Proposals that people review and Acts that people approve, which is the supervision the rule asks for.

### Attested and declared hosts

Crucible can vouch only for model calls it sees. The hosted crew makes its own calls, and an attested client routes its model traffic through `apps/model-gateway`; every other host is `Declared`.

**Decision D-AGT-34:** A host outside the model gateway is `Declared` and its contexts start `data_untrusted`; a client behind the gateway is `Attested`, and is clean only while its model requests pass the gateway's taint check.
*Why:* a host's model may have read a poisoned page or another server's output first, and attestation alone proves only which key called and which model answered.
*Rejected:* "clean as far as Crucible saw"; budgets on declared tokens; trusting self-reported tool inventories; treating every attested client as clean.

The taint check runs on every model request. The gateway marks the context `instruction_tainted` when a request contains a tool result or user turn other than a server-signed Crucible response or the delegating human's goal. It records the tool inventory from each request's tool list, and a client whose tools include anything outside Crucible is attested but never clean. A `Declared` host's model, tools and token counts are recorded as stated and never trusted, so declared tokens never bound spend.

An attested client is pre-registered and authenticates with `private_key_jwt` from a hardware key [OpenID Connect Core]. The gateway enforces the endpoint allowlist and records the model in provenance.

### Quarantined extraction

Roles that need facts from untrusted documents use the Dual LLM pattern [Beurer-Kellner et al. 2025], as Microsoft's FIDES labels do [Microsoft FIDES]. `std::agents::extract` runs a model with no tools and no other context, which fills a templated Ingot record that is schema-validated, range-checked and `data_untrusted`. It ships in phase 2; until then external text reaches agents only as handles.

**Decision D-AGT-25:** Outside the hosted crew, `read.external_text` returns only quarantined typed extracts, and inside it a context fetches web content only while its label is `public`.
*Why:* a host with its own fetch or mail tools holds untrusted input, sensitive data and an outbound channel at once, and a fetch leaks data through its choice of URL or through DNS.
*Rejected:* clearance at the response alone; trusting hosts' sandboxes; a mandatory second provider for the extractor; fetches from any context that build no URL from context data.

Raw reads need the per-client flag `allow_raw_external`, set by two people, which records the declared tool inventory and is refused above `internal`. Crew fetch targets come only from the role's allowlist or from URLs in the delegating human's goal, never from tool results, and Plan-Then-Execute roles fetch during planning, before they read the design.

The extractor may share the role's model provider, since isolation comes from no tools, no shared context and a separate API project with retention off. A second provider would add a sub-processor, not isolation. `server/discover` states these rules in the server instructions.

### Write sets, protected paths and signature rules

Write sets confine edits to globs, and protected branches (`main`, `release/*` and any that policy names) reject direct writes. Protected paths (`oracles/**`, the policy repository, behaviour-version pins, recipient records) take agent writes only through Proposals at R3 or R4.

**Decision D-AGT-27:** `api` enforces contract 5.4's signature table for every human-signed record, this tab's rows included, and break-glass serves only reads, freeze, ref revert, lock release and session termination.
*Why:* one phished administrator could otherwise export a controlled programme in one action, a second list here would drift from the table, and unbounded break-glass voids the rule.
*Rejected:* single-administrator control; a separate list in this tab; no break-glass.

This tab's rows are client and endpoint clearance, standing releases, `allow_raw_external`, training opt-in and the auto-merge policy. Under break-glass every other call fails with `auth/break_glass_forbidden`. Policy Proposals from a context with either integrity flag are refused with `label/untrusted_context`.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Instruction authority | Four sources; every `ExternalText` value returned as a handle | Injected instructions change no consequential action | AGT-O-INJ-1 | 1 |
| Free-text handles and endorsement | Value-level text integrity; signed endorsement under the signature table | `auth/human_only` | AGT-O-INJ-1 | 1 |
| Context labels and write-down | Join of returned values; (user, client identity) for hosts; write-down on confidentiality | `label/write_down` | AGT-O-LABEL-1 | 1 |
| Context reset | `session.reset_context`, by a person with WebAuthn, audited | `auth/human_only` | AGT-O-LABEL-1 | 1 |
| `Declared` hosts | Contexts start `data_untrusted`; declared tokens recorded, never enforced | None: classification cannot fail | AGT-O-RISK-1 | 1 |
| Gateway taint check | Unsigned tool results or user turns taint; tool inventory from the request; non-Crucible tools never clean | None: the gateway always records | AGT-O-LABEL-1 | 2 |
| Quarantined extraction | Tool-free, templated, schema-validated, isolated project | Invalid output dropped and reported | AGT-O-INJ-1 | 2 |
| External-host raw reads | Extracts only; `allow_raw_external` at `internal` or below | `label/raw_external_forbidden` | AGT-O-INJ-1 | 1 |
| Crew web fetches | Only while the context is `public`; allowlist or goal URLs only | `label/fetch_forbidden` | AGT-O-INJ-1 | 2 |
| Protected paths | Agent writes only through Proposals at R3 or R4 | `edit/protected_path` | AGT-O-POL-1 | 1 |
| Signature rules | Contract 5.4's table enforced at `api`; bounded break-glass | `propose/policy_unsatisfied`, `auth/break_glass_forbidden` | AGT-O-POL-1 | 1 |

## Clearance, egress and data protection

A model provider that reads a prompt holds its contents, so every model endpoint is cleared like a recipient, and every byte that leaves a tenant passes an exit that checks it.

### Endpoint and client clearance

**Decision D-AGT-19:** Every model endpoint and external client carries a clearance, a confidentiality and usage bound granted under the signature table, and only the hosted crew or an attested client clears above `internal`.
*Why:* metadata documents cannot stop localhost impersonation [MCP authorization security] or show where a host forwards content, and a hosted model decrypts prompts, which the ITAR encryption carve-out forbids third parties.
*Rejected:* clearance by metadata document; host-side filtering; model redaction; counsel ruling per endpoint rather than once on the template.

A context receives only values that both it and its human are cleared for. `controls` clear only inside the organization's boundary or under a `ControlAuthorization`, and a newly registered `Declared` client is cleared for `public` until an administrator raises it. A `Declared` client never clears above `internal`, any `controls`, any `scopes`, or a `DataLicence` that forbids disclosure to processors, and asking for more fails with `label/client_unattested`. The crew and gateway arrive in phase 2, so phase 1 agent contexts stay at `internal` or below. A `ControlAuthorization` for a provider uses the regulated cloud's basis (US persons, US regions), never an encryption carve-out.

Crucible provides mechanisms, and the organization decides what is lawful; classified information is out of scope (contract 13.1). The EAR carve-out needs end-to-end encryption with FIPS 140-2 or successor modules and no intentional storage in a Country Group D:5 country [15 CFR 734.18]. The ITAR carve-out needs unclassified data, FIPS 140-2 or AES-128 strength, no §126.1 country and an authorized recipient [22 CFR 120.54 eCFR]. No third party may hold the means of decryption [22 CFR 120.54]. An ITAR release includes exchanges with foreign persons [22 CFR 120.56], so a model endpoint is a recipient.

### The three exits

Tenant bytes leave Crucible through three exits, and each compares both the confidentiality and the usage parts of the label (contract 7.6):

1. **`release_data` Acts**, the one Act family that sends tenant data to another party ([Acts and approvals](#acts-and-approvals)).
2. **`api` responses to model contexts** cleared for them, which reach the model's provider.
3. **Audited local writes** by a person: `public` or `internal` payloads with no `controls`, no `scopes` and only licences that permit the disclosure, with a per-call assertion above `public`.

| Channel | Control |
| --- | --- |
| Uncleared endpoint or client | Clearance at the response |
| Lower-labelled repository | Write-down |
| Bytes to another party | `release_data` |
| An external host's own tools | Extracts only |
| Crew web fetches | Only from `public` contexts, to allowlisted or goal URLs |
| URLs in agent output | Inert text unless allowlisted; external images never load in review |
| Hosted crew runtime | Egress only to the API, cleared endpoints and quarantined fetches |
| Read volume | Bytes per context against the role's baseline; alert, optional freeze |

### Audit and personal data

KLN owns the audit log, its envelope and its rule of ids and digests, never labelled content. AGT owns each entry's `api`-call payload: chain, session, method, argument digest, status, labels, cost, client and trace. Act plans, approvals and policy changes are separate labelled CAS records that the entry names by `ObjectId`.

**Decision D-AGT-32:** Provenance, transcripts and API logs follow KLN's pseudonymous ids, crypto-shreddable identities and retention locks with a recorded `retention_basis`, and keep 12 months by default.
*Why:* GDPR Article 17(3)(b) covers only Union or Member State law and 17(3)(e) legal claims [GDPR Article 17], so a US duty needs its own recorded basis.
*Rejected:* names in entries; one seven-year retention for everything; a second retention rule in this tab, since two owners drift.

Release records keep their own, longer retention. Agent presence and per-person analytics have a works-council mode, since German law gives works councils co-determination over devices that monitor employees [BetrVG section 87]. Crucible ships records-of-processing entries, an impact assessment template and its model sub-processors with their regions and retention.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Endpoint and client clearance | Confidentiality and usage bounds granted under the signature table; new `Declared` clients at `public` | `label/exceeds_clearance` naming a cleared endpoint | AGT-O-LABEL-1 | 1 |
| Attested clients and model gateway | `private_key_jwt` from a hardware key; the gateway records the model | `label/client_unattested` | AGT-O-LABEL-1 | 2 |
| Control defaults | `controls` only to in-boundary endpoints or under a `ControlAuthorization` | `label/exceeds_clearance` | AGT-O-LABEL-1 | 1 |
| Exits | Three exits, each comparing confidentiality and usage | `label/exceeds_clearance`, `label/licence_forbids` | AGT-O-EXIT-1 | 1 |
| Egress monitoring | Read-volume baselines per role | Alert; optional freeze | AGT-O-INJ-1 | 2 |
| Audit payload | `api`-call fields inside KLN's entries; labelled records by `ObjectId` | A missing entry fails the call | AGT-O-AUDIT-1 | 1 |
| Personal data | KLN's pseudonymous ids and retention locks; 12-month transcripts | A lock blocks shredding with its basis recorded | AGT-O-AUDIT-1 | 2 |

## Acts and approvals

Some effects cannot be reverted by a forward Change: a file sent to a supplier, a release others build on, a program sent to a machine. Each of these is an Act, prepared as an exact plan and run only after a named person approves that plan.

### Act kinds

Every Act is two-phase: `act.prepare` produces a plan with a digest, and `act.commit` runs only after an assigned human Approval of that digest (contract 7.6). Waivers, endorsements and declassifications are signature records, not Acts.

| Act kind | Family | Effect | Reversibility | Phase |
| --- | --- | --- | --- | --- |
| `release` | Record | A signed release tag, with deliveries to the organization's own systems | Superseded by a change order | 1 |
| `yank_package` | Record | A registry version marked yanked or deprecated | Never deletes | 2 |
| `send_to_supplier` | Data release | Files for quotation or production | Irreversible | 1 |
| `export` | Data release | A repository archive or release bundle; a Git mirror, a branch shared with another organization or a message to a connector | Irreversible; sharing revocable going forward | 1 (archive, bundle), 2 (others) |
| `request_quote`, `order` | Data release | Requests for quotation and purchase orders | Orders compensable | 2 |
| `standing_release` | Data release | Bounded recurring transfers on one channel | Revocable going forward | 2 |
| `publish_package` | Data release | A public registry version | Yankable | 2 |
| `publish_passport` | Data release | A digital product passport (MFG) | Superseded | 3 |
| `send_to_machine` | Physical effect | A program or recipe of an MFG kind, through the machine gateway | Irreversible once run | 2 |
| `send_robot_program` | Physical effect | A robot program file into the controller's program store | Irreversible once run | 2 |
| `send_print_job`, `start_print` | Physical effect | A print job; the one restricted start | Cancellable | 2 |
| `bench_session` | Physical effect | Repeated transfers to one device within approved bounds | Ends on expiry or early | 2 (machines, printers), 3 (boards) |
| `run_rig_test` | Physical effect | A test on a rig under an `unattended_safe` site safety record | Irreversible | 2 |
| `store_machine_job` | Physical effect | An OPC UA job `Store`, never a start | Revocable before start | 3 |
| `flash_device` | Physical effect | A Software item image to a named board, read back, target held | Irreversible once released | 3 |

**Decision D-AGT-36:** The Act kinds are contract 7.6's list and no more: sharing with another organization and connector messages are `export` Acts, and deprecation is a mode of `yank_package`.
*Why:* each extra kind needs its own plan schema, approval page and oracle, while these differ only in channel and recipient, which the plan already names.
*Rejected:* separate kinds for sharing, outside notifications and deprecation; a deviation Act, since a deviation is a Waiver.

### Plans and the approval page

**Decision D-AGT-20:** `act.prepare` yields a deterministic `ActPlan` whose digest is the approval subject, `act.commit` returns only a request id to the model, and approvers decide on a page on its own origin.
*Why:* a URL that reaches a model can be forwarded to a busy approver as a phishing link [MCP elicitation], and script injected on the main origin could otherwise start a ceremony.
*Rejected:* URL or form elicitation in the host; approval by any authority holder; open-ended pre-approvals; approval on the main origin.

```rust
pub struct ActPlan {
    pub digest: Sha256,                  // over the canonical plan; the approval subject
    pub kind: ActKind,
    pub effects: Vec<Effect>,            // one Approval covers every effect
    pub recipients: Vec<RecipientId>,    // KLN RecipientRecords, internal systems included
    pub subject: Option<ObjectId>,       // release: ApprovalSubject; program: ProgramSubject
    pub device: Option<DeviceTarget>,    // class, serial, location, program number, what it replaces
    pub authorization: Option<ControlAuthorizationId>,
    pub standing: Option<StandingReleaseId>, // a transfer under a standing release
    pub labels: Labels,                  // payload joined with the preparing context
    pub requested_by: Vec<PrincipalId>,
    pub expires: Timestamp,              // default 24 h
}
```

The approval origin is its own WebAuthn relying party [W3C WebAuthn Level 3], and approvers use an approval credential. It serves only server text under `default-src 'none'`, with scripts allowed by hash, and accepts no cross-origin requests. Its cookies are host-only and `__Host-`-prefixed, so no other origin of the site can set them [MDN Set-Cookie]; it rejects any request that carries another cookie and publishes no WebAuthn related-origins file. Hosted deployments put it on a separate registrable domain.

Each WebAuthn challenge follows KLN's signature-record definition ([KLN, signature records](05-kiln-repo-plm.md#signature-records)). The signed `ObjectId` is the plan digest, so the challenge binds digest, meaning, signer and request id with a fresh server nonce.

Native clients open the approval origin in a browser session bound to the request id (`ASWebAuthenticationSession` on Apple platforms, the default browser elsewhere) and return by a `crucible://` callback. Apps may use passkeys only for associated domains [Apple passkeys], so every client, Crucible's cloud included, approves in this browser session, which PLT's `Authenticator` opens.

The page shows contract 7.6's contents, the physical-effect part included, plus integrity flags and a banner for recipient records changed within the last 7 days. The session's purpose appears collapsed below the typed content as a handle with its integrity flags, and text from an `instruction_tainted` context carries a banner naming the taint sources. `act.prepare` rejects invisible, tag, bidirectional and zero-width characters with `act/payload_rejected`, and a plan changed after approval fails with `act/plan_changed`. Approvals are single-use, except that a release Approval covers operators' pulls of the released program at qualified serials of its machine class.

### Three outcomes

Approvers reject work routinely to say "fix this", so a rejection must not punish the person who fixes it. The page offers three outcomes (contract 7.6):

| Outcome | Effect | What the preparer meets |
| --- | --- | --- |
| Approve | `act.commit` proceeds | `ActReceipt` |
| Return for changes | Closes the request with a reason and no penalty | A new plan with a different digest may be prepared at once; resubmitting the same digest fails with `act/returned_unchanged` |
| Deny as suspicious | Freezes the session and blocks re-preparing a plan to the same recipients for 24 h | `act/denied_cooldown` |

A plan prepared with an agent in its delegation chain counts against a limit of three pending requests per delegating human, across all sessions, so ten sessions cannot flood an approver. People preparing their own plans batch effects into one plan instead.

### Releases and signatures

A release plan's digest covers the `ApprovalSubject`'s `ObjectId`, the tag and the effectivity, never the `ChangeId` or the CI report. The subject holds every affected Item's `ItemDefinition` digest (contract 5.6), so swapped firmware, Material versions or documents void the approval. `act.commit` recomputes the subject and refuses a mismatch with `act/subject_mismatch`. A rebase that keeps the subject keeps its approvals, which are also the change order's.

Every Approval becomes a signature record that verifies offline. AAL3, the highest NIST authenticator assurance level, applies to physical-effect Acts and Acts with `controls`, since Acts have no risk class. A credential enrolled in the last 24 hours never approves either, and enrolment is itself approved under the signature table (contract 5.4). In a phone browser, a person may approve release and change-notice Acts without `controls` or physical effect, using a roaming security key; Crucible's phone apps offer no approval. The events `act.prepared`, `act.approved`, `act.returned`, `act.denied` and `act.committed` carry ids and states only.

[[DIAGRAM diagrams/09-agents-act-sequence.jsx: Act sequence · two-phase commit with the approval out of band]]

Read the diagram top to bottom: solid arrows are requests, dashed arrows replies, and the highlighted arrow is the approval that no model can give.

### Data release

**Decision D-AGT-30:** Every transfer of tenant data to another party goes through one Act family, `release_data { recipient, payload, purpose, authorization }`, checked by KLN's release stage at `act.commit`.
*Why:* six egress paths invite attackers to the weakest one, and saving a 3MF file for one's own slicer needs no approval.
*Rejected:* per-path controls; recipient records changed by ordinary Proposals; an Act for every local save.

The other two exits are `api` responses to cleared model contexts and audited local writes. Recipients are verified, screened `RecipientRecord`s, so a recipient named only in agent text fails with `act/recipient_unverified`, and an injected "our address has changed" email cannot redirect a request for quotation. The stage checks, in order:

1. The payload's confidentiality label against the recipient's clearance, and each `DataLicence`'s redistribution terms.
2. Restricted-party screening at every commit against lists at most 24 hours old, recorded by version: the daily US Consolidated Screening List [ITA Consolidated Screening List], plus EU and UK lists where policy names them. Internal recipients are screened from phase 2 (contract 13.2).
3. A `ControlAuthorization` for any payload with `controls`.
4. Audit, and from phase 3 a watermark record and expiry (KLN, ECO).

A release or change-notice plan lists its deliveries to the organization's own systems, such as ERP (enterprise resource planning), MES (manufacturing execution) and enterprise PLM (product lifecycle management), under one Approval, and failed deliveries retry until the plan expires. Recipient-record changes follow the signature table, never come from a flagged context, and take effect after 24 hours with notice. Webhooks carry thin payloads without design content (ECO).

**Decision D-AGT-33:** Recurring flows use `standing_release`, one plan approved by two people that fixes recipients, channel, payload schema, label ceiling and an expiry of at most 12 months.
*Why:* an approval per ERP message or per push to a shared branch gets rubber-stamped or bypassed.
*Rejected:* one approval per message; unbounded pre-approvals; exempting connectors or human pushes.

Each later transfer is an effect of that plan, checked mechanically by the release stage. A channel is a connector, a shared branch or a mirror. Transfers are audited and summarized weekly to the approvers, and anything over the ceiling or off-schema needs an ordinary Act. Human and agent pushes to shared branches, mirror pushes and federation sync pass the same stage.

### Physical effects

Contract 7.6 fixes the physical-safety rules: no device starts except through the restricted `start_print`, only assigned humans approve, and the person at the device starts it. This tab adds what turns those rules into code.

**Decision D-AGT-31:** Every physical-effect Act kind has a typed plan schema that cannot express a start, and an oracle captures the wire against real device servers and simulators to show that no transfer carries one.
*Why:* OctoPrint, Moonraker and PrusaLink start prints from an upload flag, so an interface without a start method is necessary but not enough.
*Rejected:* remote starts through OPC UA job methods; agent-committed transfers; static interface review alone.

- **Plans** name the device class, serial, location, controller version, program number and the program the transfer overwrites. The machine gateway checks the Approval against its pinned approver directory (MFG).
- **OPC UA.** Crucible calls `Store` only in `store_machine_job`, and `Cancel`, `Clear` and `RevokeStart` only on its own unstarted jobs; every other job-control method is uncallable [OPC 10031-4].
- **Bench sessions.** A `bench_session` plan names the person at the device, its serial, the probe or gateway and the payload kind. It also fixes one Software item or program lineage on one branch, a maximum count, an expiry of at most 8 hours and the hazard acknowledgements. Transfers inside it need no further Approval and keep every check (read-back, hold in reset, no start, the gateway's offset check, the canonical program hash). It ends on expiry, on a hazard change or on a payload outside the lineage, agents never open or extend one, and the approval page lists every transfer afterwards.
- **Firmware.** `flash_device` leaves the target held for a person at the bench. Client flashing runs only in code that verifies the Approval: the approval-origin page in browsers, which alone holds the WebUSB grant and checks the image's SHA-256, and `apps/platform-*`'s flashing service on desktops. The main web origin never holds a WebUSB grant.
- **Small shops.** MFG's minimum-ceremony table says how a one-person shop runs ([MFG, approval and transfer](07-manufacturing.md#prove-out-and-the-minimum-ceremony)). A program Item starts in `Prototype` with its first transfer plan. The Cedar policy `self_approve_transfer`, off by default and enabled by the site's safety officer, lets the person who prepared a transfer approve it with AAL3.

Physical-effect kinds ship with MFG's transfers in phase 2, `store_machine_job` with the OPC UA path in phase 3, and `flash_device` with ELX's Software items in phase 3.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Two-phase Acts | Deterministic plan digest; commit after an assigned Approval | `act/plan_changed`, `act/denied` | AGT-O-ACT-1 | 1 |
| Act kinds | Contract 7.6's list; sharing and connector messages as `export`; deprecation as a yank mode | `act/kind_unknown` | AGT-O-ACT-1 | 1 |
| Approval requests | Cedar-assigned; inbox only; request id to the model; approval credentials | "Not assigned to you"; an unenrolled credential is refused | AGT-O-ACT-1 | 1 |
| Approval origin | Own origin and relying party; strict content policy; `__Host-` cookies only; KLN's challenge; browser sessions for native clients | A main-origin ceremony or a tossed cookie fails | AGT-O-ACT-1 | 1 |
| Approval page | Contract 7.6 contents; collapsed purpose with taint banner; integrity flags; recipient banner | `act/page_unrenderable` refuses the request | AGT-O-ACT-1 | 1 |
| Approval outcomes and limits | Approve, return for changes, deny as suspicious; three pending per delegating human for agent-prepared plans | `act/returned_unchanged`, `act/denied_cooldown` | AGT-O-ACT-1 | 1 |
| Character rejection | Invisible, tag, bidirectional and zero-width characters refused | `act/payload_rejected` | AGT-O-ACT-1 | 1 |
| Release Acts | Digest over the approval subject; subject recomputed at commit; offline-verifiable signature records | `act/subject_mismatch` | AGT-O-ACT-1 | 1 |
| Data-release family | Recipient clearance, licences, screening, `ControlAuthorization`, audit | `act/recipient_unverified`, `label/exceeds_clearance` | AGT-O-EXIT-1 | 1 |
| Watermark and expiry | Watermark record and expiry on data release (KLN, ECO) | Delivery refused without them | AGT-O-EXIT-1 | 3 |
| Standing releases | Fixed recipients, channel, schema, ceiling, expiry; weekly digest | An over-ceiling or off-schema payload is refused | AGT-O-EXIT-1 | 2 |
| Physical-effect Acts | Transfer only; plan schemas without a start; allowlisted OPC UA methods; restricted `start_print` and rig tests | `act/onsite_required` | AGT-O-SAFE-1 | 2 |
| Bench sessions | One AAL3 Approval over person, serial, probe, lineage, count, expiry of at most 8 h and hazards; every transfer checked | `act/bench_session_ended` | AGT-O-SAFE-2 | 2 (machines, printers), 3 (boards) |
| Firmware flashing | `flash_device` with read-back, target held; client flashing only in Approval-verifying code | `act/onsite_required` | AGT-O-SAFE-1 | 3 |

## Model independence

Every guarantee lives in the server, so models differ in how well they work, never in what they may do.

**Decision D-AGT-21:** The hosted crew calls models through one Rust trait, `ModelEndpoint`, with adapters for hosted APIs and local OpenAI-compatible servers, never through MCP Sampling.
*Why:* MCP 2026-07-28 deprecates Sampling in favour of direct provider APIs [MCP changelog], and one trait keeps the choice of provider a configuration decision.
*Rejected:* Sampling, which is deprecated; a single provider, which the founder's requirements and air-gapped installs rule out.

```rust
pub trait ModelEndpoint: Send + Sync {
    fn record(&self) -> &EndpointRecord;            // weights digest or dated provider version, region
    fn capabilities(&self) -> &ModelCapabilities;   // tool calling, vision, context, structured output
    fn clearance(&self) -> &Labels;                 // granted under the signature table
    async fn complete(&self, req: CompletionRequest) -> Result<CompletionStream, ModelError>;
}
```

An `EndpointRecord` pins a local endpoint's weights digest or a hosted one's dated version, and registry weights are signed. An endpoint qualifies for a role by passing the role's golden tasks at its pass^1 and pass^4 thresholds, and the qualification is bound to the record. Here pass^k is the share of tasks completed in every one of k independent trials.

| Missing capability | Degradation |
| --- | --- |
| Vision | `visible_summary`, structured marks and `inspect.describe`; the role runs only if qualified in text-only mode |
| Native tool calling | JSON mode with schema validation and two repair retries; otherwise unqualified |
| Long context | Smaller pages, outlines before source, concise detail |
| Endpoint unavailable | Backoff, then the role's next qualified endpoint, recorded in provenance |
| No qualified endpoint | `crew/no_qualified_endpoint` with the qualification results; never a silent downgrade |

Identical behaviour is claimed only for Crucible's side: every crew model call stores a CAS replay record, so a session's API calls replay exactly.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| External hosts | Any MCP 2026-07-28 client under server enforcement; `Declared` | Typed `auth` and `label` errors | AGT-O-MCP-1 | 0 |
| Hosted crew | `apps/crew` over the public SDK; per-tenant instances | `crew/no_qualified_endpoint` | AGT-O-BENCH-1 | 2 |
| Endpoint records | Weights digest or dated version; re-qualification on change | An unqualified endpoint is refused | AGT-O-PROV-1 | 2 |
| Qualification and degradation | Per-role suites and thresholds; declared degradations | Never a silent downgrade | AGT-O-BENCH-1 | 2 |
| Replay records | Every crew model call in CAS | `crew/replay_missing` blocks the session's provenance | AGT-O-PROV-1 | 2 |

## Benchmarking, training data and documentation

Agent quality is a feature like any other: it is measured on fixed suites, gated at every release, trained only on data Crucible may use, and taught by generated documentation.

### Suites and the release gate

Harness, suites and graders live in `oracles/agents/`, and held-out suites live outside every tree that agents read. Third-party datasets are fetched by content hash at test time, never vendored.

| Suite | What it measures | Use |
| --- | --- | --- |
| Text2CAD-Bench | Text to parametric CAD at four levels; 600 examples [Wang et al. 2026] | External comparison on exported geometry |
| CADPrompt | 200 prompts; point-cloud distance and compile success [Alrashedy et al. 2024] | External comparison |
| CADTestBench | Text to CAD verified by executable tests [Mallis et al. 2026] | Reference for check-based grading |
| MUSE | Manufacturable assemblies; the strongest models scored 19–21% on fine-grained criteria [Dong et al. 2026] | Phase 2 and later |
| Golden-product tasks | Create, edit, fix a check, add a study, DFM, CAM, change order; at least 50 per product (target) | Primary metric, release gate, endpoint qualification |
| Held-out set | The same on unseen products; at least 200 by phase 2 (target) | Overfitting control |
| Injection suite | Planted instructions in imports, comments, identifiers, string literals, templates, embossed geometry and textures; at least 100 per release (target), in the manner of AgentDojo [Debenedetti et al. 2024] | Security gate |

Text2CAD-Bench's metrics are reimplemented from the paper, since its code was not released. Golden tasks carry a starting Change, a goal, hidden acceptance checks, a reference solution and forbidden actions, and `service:ci` grades them in two platform classes. A model judge scores only documentation and requirement text, on a 0.0–1.0 rubric that people calibrate each release [Anthropic multi-agent research].

Metrics include task success, pass^1 and pass^4, edit minimality, query robustness, review acceptance, verifier catch rate, cost per success and safety violations. Reliability across trials is gated, since τ-bench found pass^8 below 25% in its retail domain [Yao et al. 2024].

Every release, and every change to `std::agents`, `apps/crew` or the MCP surface, reruns the golden tasks and the held-out set three times per endpoint. The gate fails on a success drop above 2 points (target) at 95% confidence by paired bootstrap, or on any successful injection. Red-teaming adds adaptive attackers, an outside red team before each gate, tripwires and a public bounty from phase 3.

### Training data

Models adapt through context first and are fine-tuned only where measurement shows a gain. Crucible's generator emits Ingot programs, edits, repairs of injected errors and observations paired with facts, and every item builds and reproduces from its seed, as CAD-Recode's million procedural sequences did [Rukhovich et al. 2024].

| Source | Terms | Use |
| --- | --- | --- |
| Fusion 360 Gallery Dataset | Non-commercial research only; terminable by Autodesk [Fusion 360 Gallery licence] | Never in anything that ships, in any tab |
| ABC dataset | Onshape's terms, which vary by document date and LICENSE tab [Onshape terms] | Only contract 13.3's licence-filtered subset with ECO's per-model licence proof: benchmarks and published measurements, and training as the rule below allows |
| DeepCAD and derivatives | Parsed from Onshape public documents linked from ABC [DeepCAD README] | As ABC, model by model |
| Public CAD benchmarks | Licences not stated on the pages opened | Evaluation only, after licence review |
| Procedural data, std, golden products | Crucible's own | Unrestricted |
| Customer data | Owned by the customer | Opt-in only |

**Decision D-AGT-22:** Every shipped model trains only on procedural data, std, golden products, opted-in customer data and data with per-item proof of a commercial licence.
*Why:* weights inherit the obligations of their data, the Fusion 360 Gallery forbids commercial use, customers own their geometry, and Onshape's grant varies per document.
*Rejected:* research-use exceptions, ECO's segmentation models included; scrubbed confidential corpora; scraped CAD models; dataset-level licence assumptions.

Cross-tenant training admits only `public` items or items whose `DataLicence` permits it, never `confidential` items or third-party Assets. Per-tenant weights serve one tenant. Opt-in is off by default and set per repository by two people, with eligibility decided per item. Shared corpora are deduplicated, exclude identities and comments, and must not leak planted canaries, and a withdrawal removes affected shared models within 30 days.

### Agent-facing documentation

**Decision D-AGT-23:** All agent-facing documentation is generated from the Rust method types, Ingot doc comments and the error catalog, pinned to versions, and `read.docs` answers for the repository's lockfile.
*Why:* stale docs teach agents wrong APIs, and version-pinned answers match the code the agent edits.
*Rejected:* hand-written agent docs, which drift; retrieval over the web, which is unversioned and untrusted.

Examples compile in CI, and a failing one blocks the release. Crucible publishes per-method and std references, an error catalog with examples and fixes, skills and an `llms.txt` index. Pages run about 2,000 tokens (target) and are benchmarked like code, because tool descriptions measurably help agents [Anthropic writing tools]. A grant exposes at most 60 tools, and a new method needs a benchmark gain over composing existing ones. Deprecations carry a machine-applicable fix for 12 months, and CI fails a public std item without a doc comment, an example or units.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Benchmark harness | Suites above, graded by checks in two platform classes; datasets fetched by hash | `bench/dataset_hash_mismatch` refuses the suite | AGT-O-BENCH-1 | 1 |
| Release gate | Three trials per task per endpoint; a 2-point drop at 95% or any injection fails | Release blocked | AGT-O-BENCH-1 | 1 |
| Injection suite | Planted instructions across every text and image channel | The gate fails on any success | AGT-O-INJ-1 | 1 |
| Verifier efficacy | Planted-defect catch rate | The gate fails below target | AGT-O-VER-1 | 2 |
| Procedural corpus | Items build; reproducible from seeds | Failing items excluded | AGT-O-DATA-1 | 2 |
| Training eligibility | Per-item labels, licences and proof; canary tests; 30-day withdrawal | Ineligible items excluded and reported | AGT-O-DATA-1 | 3 |
| Generated references | Methods, std and errors from source, pinned to versions | A failing example blocks the release | AGT-O-DOCS-1 | 0 (errors), 1 (std) |
| Lockfile-pinned answers | `read.docs` for the repository's lockfile | `docs/not_found` with nearest matches | AGT-O-DOCS-1 | 1 |
| Tool surface | At most 60 tools per grant; group prefixes | A new method without benchmark gain is refused in review | AGT-O-BENCH-1 | 1 |

## Reference

### Method catalog

Every method is `<group>.<name>` in contract 7.6's eight groups, which ECO's and KLN's methods join. A breaking change creates a version such as `edit.apply@2`, and the previous one is served for at least twelve months. Methods marked † change state or spend budget, so they need an idempotency key and, except `session.open`, a session. Read and Inspect methods accept a `ChangeRef`, every result carries its labels, and every `ExternalText` value in a result is a handle. Approvals are not methods: assigned people give them on the approval page.

Sessions emit the events `session.called` (method, status, audit entry, usage), `session.asked`, `session.answered`, `session.controlled` and `session.closed`. They carry ids and states only, and UIX's agent panel reads them.

| Method | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `session.open` † | `SessionOpen` → `SessionOpened` | `auth/scope_denied`, `session/branch_protected`, `label/exceeds_clearance` | AGT-O-POL-1 | 0 |
| `session.status` | Handle → head, grant, context label, usage, open Evaluations and questions | `session/expired` | AGT-O-MCP-1 | 0 |
| `session.ask` † | A typed question with an answer schema → the delegating human's answer as typed data; one blocking question per session | `session/question_expired` | AGT-O-POL-1 | 1 |
| `session.close` † | Handle → final usage; unused budget returned | `session/unknown` | AGT-O-BUD-1 | 0 |
| `session.reset_context` † | A person resets an external host's context label with WebAuthn after clearing its conversation; audited | `auth/human_only` | AGT-O-LABEL-1 | 1 |
| `session.control` † | Pause, resume or steer a hosted-crew session; delegating human only | `auth/not_delegator` | AGT-O-POL-1 | 2 |
| `session.presence` † | Share selection or camera with an agent session; delegating human only | `auth/not_delegator` | AGT-O-POL-1 | 2 |
| `read.tree` | Path → entries with kind, size, hash and labels | `read/not_found` | AGT-O-MCP-1 | 0 |
| `read.source` | Path, range → text with untrusted free-text spans as handles | `read/not_found`, `label/exceeds_clearance` | AGT-O-INJ-1 | 0 |
| `read.outline` | Path or feature → calls, parameters, checks, spans | `build/parse_failed` (partial outline) | AGT-O-MCP-1 | 0 |
| `read.history` | Branch → Changes with provenance; messages as handles | `read/not_found` | AGT-O-PROV-1 | 0 |
| `read.branches` | Repository → name, head, protection, owner | `read/not_found` | AGT-O-MCP-1 | 0 |
| `read.symbols` | Query → path, kind, signature, doc URI | `read/not_found` | AGT-O-DOCS-1 | 1 |
| `read.language_service` | An LSP 3.17 request (completion, hover, inlay hints, semantic tokens, code actions) at a Change → ING's result | `read/request_unsupported` | AGT-O-MCP-1 | 1 |
| `read.docs` | Symbol, error code or URI → `DocEntry`s pinned to the lockfile | `docs/not_found` with nearest matches | AGT-O-DOCS-1 | 0 (errors), 1 (std) |
| `read.external_text` | Handle → typed extract, or raw text where the extraction rules allow | `label/raw_external_forbidden` | AGT-O-INJ-1 | 0 (handles), 2 (extracts) |
| `read.value` | `ValueRef` → typed value; marks the context `data_untrusted` | `read/unknown_handle` | AGT-O-LABEL-1 | 1 |
| `read.bom`, `read.where_used` | KLN's EBOM, then MBOM, service BOM and where-used | `read/not_found` | AGT-O-MCP-1 | 1 (EBOM), 2 |
| `read.search_items` | `class`, `where:`, `shape_like:`, `k` → readable released Items ranked by KLN's name-free shape descriptors, exact duplicates by `GeometryId` first | `read/class_unknown` | AGT-O-MCP-1 | 2 |
| `read.catalog` | Filters → catalog part summaries | `catalog/filter_invalid` | AGT-O-MCP-1 | 2 |
| `read.coverage` | Domain, scale, level, status → COV's coverage map rows and limit records | Unbacked rows show `Planned (phase n)` (COV) | AGT-O-MCP-1 | 0 |
| `read.packages`, `read.package`, `read.registry_bundle` | ECO registry search, package metadata and signed offline bundles | `package/not_found` with nearest names; `package/unavailable` (bundles) | AGT-O-MCP-1 | 1 (`read.package`), 2 |
| `read.events` | Source, cursor → events in sequence order | `events/cursor_expired` | AGT-O-MCP-1 | 1 |
| `read.subscribe`, `read.unsubscribe` | A webhook subscription with thin payloads (ECO); `maintainer` or `admin` people only | `events/url_refused` | AGT-O-EXIT-1 | 1 |
| `read.machine_data` | Machine → state and as-run records from MFG's gateway | `mfg/gateway_unreachable` | AGT-O-MCP-1 | 2 |
| `read.audit` | Filter → audit entries; needs `audit:read` | `auth/scope_denied` | AGT-O-AUDIT-1 | 1 |
| `inspect.scene` | Root, depth, include → `SceneGraph` | `build/failed` (partial graph), `inspect/too_large` (cursor) | AGT-O-OBS-1 | 1 |
| `inspect.entity` | Entity → kind, surface type, size, adjacency, provenance chain | `inspect/entity_gone` with `HistoryRecord`s | AGT-O-OBS-1 | 1 |
| `inspect.query` | Ingot query → entities with notes; `stability: true` adds ANV's sampled analysis | `query/resolve_failed` with candidates | AGT-O-OBS-3 | 1 |
| `inspect.suggest_query` | Entities → robust queries with sampled stability scores | `query/no_robust_candidate` | AGT-O-OBS-3 | 1 |
| `inspect.measure` | Distance, angle, clearance, thickness, mass, interference → `Quantity`, `ErrorBound`, witnesses | `inspect/kind_unsupported` | AGT-O-OBS-1 | 1 |
| `inspect.render` | `RenderRequest` → `Rendered` Snapshot from `apps/headless-render` | `render/too_many_marks` | AGT-O-OBS-1 | 1 |
| `inspect.ask_render` | `std::agents` template, marks → mark ids, booleans or counts as `ValueRef`s | `render/template_unknown` | AGT-O-INJ-1 | 2 |
| `inspect.section` | Plane → curves, SVG, legend | `inspect/empty_section` with the nearest offset | AGT-O-OBS-1 | 1 |
| `inspect.field` | Points, region, statistics or extrema → values with error and zones | `field/out_of_domain` | AGT-O-OBS-1 | 1 |
| `inspect.describe` | Target, detail → `Description` | `build/failed` (describes what built) | AGT-O-OBS-2 | 0 |
| `edit.apply` † | `ApplyEdits` → `EditsApplied` | `edit/*`, `label/write_down` | AGT-O-API-2 | 0 |
| `edit.stream` † | Override updates to a subscription; ends in one `edit.apply` or a discard | `edit/override_site_unknown` | AGT-O-API-2 | 1 |
| `edit.revert` † | Changes → a forward Change | `edit/revert_conflict` | AGT-O-API-2 | 0 |
| `edit.undo` † | One repository transaction from KLN's log; own branches only | `edit/not_owner` | AGT-O-API-2 | 0 |
| `edit.create_branch`, `edit.reset_branch` † | Create an own branch; reset an own unprotected branch | `edit/branch_exists`, `edit/branch_protected` | AGT-O-API-2 | 0 |
| `edit.import_archive` † | ECO archive → a new design repository; spans untrusted unless the server that witnessed each write signed its span-integrity record (KLN) | `archive/incomplete` listing missing objects | AGT-O-MCP-1 | 1 |
| `edit.grant_capability`, `edit.revoke_capability` † | A Wasm component capability grant or revocation in `ingot.lock` (ECO) | `policy/denied` naming the rule | AGT-O-POL-1 | 1 |
| `evaluate.build` † | Targets, `Fidelity`, `estimate_only` → `EvaluationReport` | `budget/exceeded`, `build/failed` | AGT-O-BUD-1 | 0 |
| `evaluate.checks` † | Selection, `Fidelity` → `CheckOutcome`s | `budget/exceeded`, `build/failed` | AGT-O-MCP-1 | 0 |
| `evaluate.subscribe` † | Targets, overrides, fidelity ceiling → a frame stream under the `Drag` class | `budget/exceeded` | AGT-O-API-2 | 1 |
| `evaluate.simulate` † | Study, `Fidelity` → Fields with `ErrorBudget`s and zones | `flux/study_invalid`; zones flag, never hide | AGT-O-MCP-1 | 1 |
| `evaluate.manufacture` † | Setup → toolpaths, collisions, removal, cycle time | `mfg/setup_invalid` | AGT-O-MCP-1 | 2 |
| `evaluate.cost` † | Quantity, process → cost lines with intervals and price sources | `cost/unpriced_lines` (partial report) | AGT-O-MCP-1 | 1 |
| `evaluate.ci` † | Change → the `CiReport` that Proposal CI would produce | `budget/exceeded` | AGT-O-RISK-1 | 1 |
| `evaluate.explore`, `evaluate.materialize` † | Exploration → Pareto frames; a variant → `SetParameter` edits | `explore/no_feasible_point`, `explore/variant_unknown` | AGT-O-EXP-1 | 2 |
| `evaluate.get` | Evaluation, `after_frame`, `wait_ms` ≤ 25,000 → status, frames | `evaluation/unknown` | AGT-O-MCP-1 | 0 |
| `evaluate.cancel` † | Evaluation → status; cancellation is an Abort | `evaluation/unknown` | AGT-O-MCP-1 | 0 |
| `compare.diff` | From, to, levels → `SemanticDiff`, optional overlay | `compare/unrelated` (flagged) | AGT-O-RISK-1 | 1 |
| `compare.merge_preview` | Base, left, right → KLN's conflicts and result, nothing written | `compare/unrelated` | AGT-O-API-2 | 1 |
| `compare.resolve` | Manifest, lockfile → a new lockfile and its diff, not applied (ECO) | `package/unsatisfiable` with the explanation | AGT-O-MCP-1 | 1 |
| `propose.create`, `propose.update` † | Title, rationale, target, parent, draft, ready → `Proposal` | `propose/preconditions_failed`, `propose/closed` | AGT-O-RISK-1 | 1 |
| `propose.get`, `propose.list` | Proposals, with free text as handles | `read/not_found` | AGT-O-INJ-1 | 1 |
| `propose.review` † | Verdict, findings → KLN's `ReviewVerdict` | `propose/self_review_forbidden` | AGT-O-POL-1 | 1 |
| `propose.comment` † | Anchor, body → `Comment`; @mentions of agents become inbox requests | `propose/closed` | AGT-O-POL-1 | 1 |
| `propose.merge`, `propose.withdraw` † | Expected head → merged Change, with a per-call assertion; or a reason | `propose/policy_unsatisfied`, `propose/conflict`, `auth/assertion_required` | AGT-O-RISK-1 | 1 |
| `propose.endorse_text` † | Spans → an endorsement signed by one human reader under the signature table | `auth/human_only` | AGT-O-INJ-1 | 1 |
| `propose.waive` † | A Waiver that a person signs on the approval page under the signature table; KLN stores it | `auth/human_only`, `propose/check_protected` | AGT-O-ACT-1 | 1 |
| `propose.policy` † | A Proposal to the organization's policy repository (policy packages and Cedar policies); people merge it under the signature table | `label/untrusted_context`, `auth/human_only` | AGT-O-POL-1 | 1 |
| `propose.declassify` † | A declassification record for two signers, one an export officer; KLN stores it | `auth/human_only` | AGT-O-LABEL-1 | 1 |
| `propose.plan` † | Plan → validated plan and work-item states | `plan/invalid` | AGT-O-SWARM-1 | 2 |
| `propose.change_request`, `propose.change_order` † | KLN lifecycle records; change orders approved through their release plan and KLN's review routing | `propose/preconditions_failed` | AGT-O-ACT-1 | 2 |
| `propose.mass_change` † | `from`, `to`, `scope` → KLN's mass change, run as a plan with one work item per repository under one change order | `propose/mass_change_incomplete` | AGT-O-SWARM-1 | 3 |
| `propose.purge` † | KLN purge request for two administrators | `auth/human_only` | AGT-O-POL-1 | 2 |
| `act.prepare` † | Kind, payload → `ActPlan` with digest | `act/recipient_unverified`, `act/returned_unchanged`, `label/exceeds_clearance` | AGT-O-ACT-1 | 1 |
| `act.commit` † | Plan digest → `act/approval_pending { request }` until decided, then `ActReceipt` | `act/plan_changed`, `act/subject_mismatch`, `act/returned`, `act/denied_cooldown`, `act/onsite_required` | AGT-O-ACT-1 | 1 |
| `act.status` | Plan digest → state, approvals, receipt | `act/unknown` | AGT-O-ACT-1 | 1 |

### MCP profile

| MCP element | Crucible use |
| --- | --- |
| `server/discover` | Versions, extensions and catalog version; the instructions state the external-text rules [MCP changelog] |
| `tools/list` | One tool per granted method, in deterministic order; varies by authorization only [MCP tools] |
| `tools/call` | `outputSchema` and `structuredContent` on every tool; domain failures as tool execution errors |
| Resources | Change-addressed `crucible://` URIs with long `ttlMs` and `cacheScope: "private"` |
| `subscriptions/listen` | Branch-head, Proposal and Evaluation resources and `toolsListChanged` |
| Tasks extension | Long Evaluations return tasks driven by `tasks/get`, `tasks/update` and `tasks/cancel` [MCP Tasks] |
| MRTR | `act.commit` returns `act/approval_pending` with a request id, never a URL; step-up uses `insufficient_scope` [MCP MRTR] |
| Skills extension | Role skills with SHA-256 manifests, implemented in `apps/mcp`, since `rmcp` does not list Skills [MCP Skills] |
| Apps extension | A read-only Proposal viewer (phase 2) that never approves anything [MCP Apps] |
| HTTP headers | Gateways rate-limit on `Mcp-Method` and `Mcp-Name`; `x-mcp-header` mirrors only `shard_key` |
| Not used | Sampling, Roots, Logging and HTTP+SSE |

Mirrored headers are visible to intermediaries [MCP tools], so `shard_key` is an HMAC-SHA-256 of the repository id under the tenant's routing key, truncated to 16 bytes. `requestState` is sealed with AEAD and bound to the principal, the request digest and a 15-minute expiry [MCP MRTR]. `edit.apply` becomes the tool `edit_apply`, because the Claude API allows only letters, digits, `_` and `-` in tool names [Claude tool definitions].

### Error families

Each family has one owner. `api` families name boundary failures, never method groups; tab families name each tab's typed `Failure` variants as `<family>/<snake_case>` (`SymmetryBroken` renders as `flux/symmetry_broken`, `ControllerVersionUnqualified` as `mfg/controller_version_unqualified`).

| Family | Owner | Representative codes | Typical fix |
| --- | --- | --- | --- |
| `auth` | AGT | `scope_denied`, `step_up_required`, `assertion_required`, `no_live_grant`, `human_only`, `not_delegator`, `break_glass_forbidden` | Step up; ask the delegating human for a grant or a per-call assertion |
| `session` | AGT | `expired`, `branch_protected`, `lease_lost`, `role_unavailable`, `question_expired` | Open a session; fork a branch |
| `request` | AGT | `in_flight`, `idempotency_mismatch` | Wait; reuse the original key |
| `read`, `docs`, `inspect`, `render`, `field`, `compare`, `query` | AGT | `not_found`, `unknown_handle`, `empty_section`, `too_many_marks`, `out_of_domain`, `resolve_failed`, `no_robust_candidate` | Re-read; pin a candidate; `inspect.suggest_query` |
| `edit` | AGT | `stale_base`, `patch_mismatch`, `introduces_errors`, `write_set_violation`, `protected_path`, `override_site_unknown` | Re-read and retry; apply the compiler's fix |
| `build`, `evaluation`, `explore`, `cost`, `catalog` | AGT | `failed`, `parse_failed`, `unknown`, `no_feasible_point`, `unpriced_lines` | Fix the reported diagnostic; relax a constraint |
| `budget`, `limit` | AGT | `exceeded`, `rate` | Lower the fidelity; wait |
| `propose`, `plan` | AGT | `preconditions_failed`, `policy_unsatisfied`, `self_review_forbidden`, `check_protected`, `route_incomplete`, `invalid` | The failing checks and missing approvals |
| `act` | AGT | `approval_pending`, `plan_changed`, `subject_mismatch`, `recipient_unverified`, `returned_unchanged`, `denied_cooldown`, `onsite_required`, `payload_rejected` | Wait for the assigned approver; prepare a changed plan |
| `label` | AGT | `write_down`, `exceeds_clearance`, `client_unattested`, `raw_external_forbidden`, `fetch_forbidden`, `untrusted_context`, `licence_forbids` | A new context; a cleared endpoint; a declassification |
| `crew`, `bench` | AGT | `no_qualified_endpoint`, `replay_missing`, `dataset_hash_mismatch` | Qualify an endpoint; refetch the dataset |
| `ing` | ING | `ing/3001`, `ing/4104`, `ing/6401`; lints `ing/l-fragile-selector`, `ing/l-unnamed-check` | The diagnostic's `SourcePatch` |
| `anvil` | ANV | Geometry operation failures | The failure's ranked fixes |
| `flux`, `cov` | FLX, COV | `study_invalid`, `symmetry_broken`; validity failures | Change the study; escalate the model |
| `kiln`, `repo`, `plm`, `trust` | KLN | `op_version_retired`, merge conflicts, lifecycle and signature failures | An upgrade Proposal; resolve the conflict |
| `mech`, `mfg`, `elx`, `ui` | MEC, MFG, ELX, UIX | `mfg/gateway_unreachable`, `mfg/setup_invalid`, `mfg/dnc_session_pre_armed` | The tab's typed fix |
| `package`, `archive`, `events`, `policy` | ECO | `not_found`, `unsatisfiable`, `incomplete`, `cursor_expired`, `denied` | The explanation in `context` |
| `platform` | PLT | Device, storage and runtime failures | The platform's remedy |

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Agent protocol | MCP 2026-07-28 with Tasks and Skills [MCP specification] | Fusion MCP and Fusion Data MCP [Autodesk Fusion MCP]; Onshape's FeatureScript MCP server [Onshape FeatureScript MCP] | Adopt; one catalog behind every transport, with a published approval model | AGT-O-MCP-1; transcripts pass on 5 MCP hosts (target) |
| Conversational CAD agents | Code as the medium, selection awareness, four-view self-review [Zoo Zookeeper research] | Zoo Zookeeper [Zoo Zookeeper]; NX Copilot, which answers but does not act [DE247 NX Copilot] | Ingot, `session.presence`, `Grid4`; independent verification | AGT-O-BENCH-1 |
| Tool and response design | Consolidated, namespaced tools; concise responses; actionable errors [Anthropic writing tools] | Claude Code's 25,000-token limit | At most 60 tools per grant; `detail`; a 20,000-token cap | Tokens per successful task |
| Errors and retries | RFC 9457 problem details; tool execution errors; the Idempotency-Key header [IETF Idempotency-Key] | None published for CAD agents | Idempotency keys; one error rendering with ordered fixes | The first fix resolves at least 60% (target); AGT-O-API-1 |
| Delegated identity | MCP's OAuth 2.1 profile; token exchange; DPoP [RFC 9449] | None published for CAD agents | Delegation grants, sender-constrained tokens, device agents for local credentials | AGT-O-POL-1, AGT-O-POL-2 |
| Prompt-injection defence | Design patterns; CaMeL, 77% of AgentDojo tasks with provable security against 84% undefended [Debenedetti et al. 2025]; FIDES labels; Rule of Two | CaMeL | Context labels, four instruction sources, Plan-Then-Execute, Dual LLM extraction, approved Acts. Deviation: no CaMeL interpreter around every role; *reason: maturity*; phase 3 evaluates one for tainted roles | Zero attacker-chosen consequential actions; utility under attack within 10 points of clean (targets) |
| Visual grounding | Set-of-Mark prompting [Yang et al. 2023] | Zookeeper's multi-view snapshots | Marks with structured maps, `Grid4`, text summaries | Entity-selection accuracy at least 95% (target) |
| Snapshot comparison | ꟻLIP perceptual difference [NVIDIA FLIP] | None | ꟻLIP thresholds against a pinned renderer image | AGT-O-OBS-1 |
| Design verification | CADCodeVerify; executable tests [Mallis et al. 2026] | CADCodeVerify | Checks plus a mutating verifier | Catch rate at least 90% by phase 2 (target, AGT-O-VER-1) |
| Orchestration | Orchestrator-workers [Anthropic effective agents]; parallel subagents | Anthropic's research system | Validated plans, branches, a merge queue; one agent by default | Success and cost against one agent |
| Fair sharing | Dominant Resource Fairness [Ghodsi et al. 2011] | None | Within each priority class | AGT-O-BUD-1 |
| Expensive optimization | qLogNEHVI, hypervolume knowledge gradient and scaled lengthscale priors, cited under design-space exploration | BoTorch 0.18.1 [BoTorch multi-objective] | `std::explore` in Rust | Hypervolume within 5% of BoTorch (target) |
| Cheap optimization | NSGA-II and NSGA-III | pymoo 0.6.2 [pymoo algorithms] | The same in `std::explore` | Hypervolume against pymoo |
| Text-to-CAD and editing | Text2CAD-Bench, CADPrompt, CADTestBench, MUSE, CadEval [Epoch CadEval] | Text2CAD-Bench L1: GPT-5.2, invalidity 11.1%, IoU 0.59 [Wang et al. 2026] | Ingot agents in check-driven loops | Adapted L1: invalidity at most 5%, IoU at least 0.75 (target) |
| Reliability | pass^k [Yao et al. 2024] | None | pass^1 and pass^4 per suite and endpoint | Release gate (AGT-O-BENCH-1) |
| Training data | Procedurally generated CAD programs [Rukhovich et al. 2024] | CAD-Recode | An Ingot generator whose items build | Gain on the held-out set |
| Provenance | in-toto Statement v1 [in-toto Statement] | None | Signed `ChangeProvenance` | AGT-O-PROV-1 |
| CAM assistance | Strategies accepted step by step [CloudNC CAM Assist] | CloudNC CAM Assist | CAM programmer gated by collision and gouge checks | 50% of golden programs accepted unedited (target) |

| Capability | Incumbent and its documented feature | Crucible's capability row and phase | Standing |
| --- | --- | --- | --- |
| Agents drive the CAD tool through MCP | Autodesk opens Fusion to AI workflows through the Fusion MCP [Autodesk Fusion MCP]. SolidCraft, an AI-built clone, serves `execute`, `set_parameter`, `screenshot`, `export` and similar tools on stdio [SolidCraft repository] | MCP server, 0; every UI action an API method, 0 | Ahead: one typed catalog for people and agents, with typed errors and fixes, where the clone serves a command channel with no permission model described |
| Agent writes design code and checks itself | Zookeeper writes and modifies KCL and triggers snapshots to review its own changes [Zoo Zookeeper]. Onshape's FeatureScript MCP inserts, runs and revises custom features [Onshape FeatureScript MCP] | Structured edits, 0; independent verifier, 1 | Ahead: an independent verifier with check mutation, not self-review, judges the work |
| Assistant for learning the tool | NX Copilot answers technical queries from documentation [DE247 NX Copilot] | Lockfile-pinned answers, 1 | Ahead: answers pinned to the design's own versions, and the agent can also act |
| Human review of agent work | None of the four pages describes branches, review or approval for agent edits; SolidCraft lists undo and redo as its only recovery [SolidCraft repository] | Proposal records, 1; risk classes, 1; auto-merge, 2 | Ahead: work arrives as a reviewed Proposal with a semantic diff and a risk class |
| Approval of effects outside the tool | Not described by the incumbents' agent pages | Two-phase Acts, 1; physical-effect Acts, 2 | Ahead: nothing leaves without a named person approving its exact plan |
| AI-assisted CAM programming | CloudNC CAM Assist proposes strategies a programmer accepts [CloudNC CAM Assist] | CAM programmer role, 2 | Later: CAM itself ships in phase 2 |

## Platform notes

| Target | What differs |
| --- | --- |
| Desktop | `crucible mcp` runs on stdio and authenticates as the device agent `agent:<org>/local/<device>` with `Declared` assurance; each launch joins the (user, client identity) label. Local SDKs use a domain socket or named pipe, never an open localhost port [MCP security practices] |
| Desktop without a team server | Read, Edit, Evaluate, Inspect and Compare run locally with audited local writes; Proposals and Acts need a team server (contract 13.2) |
| Browser | Agents use the TypeScript SDK over Streamable HTTP to a team server; the browser engine worker links `api`, the UI module links `api-schema`, and no model runs in the page |
| Approvals | Desktops and tablets approve in a browser session on the approval origin; macOS, iPadOS and Android approve with a roaming security key, since their platform passkeys are synced; phones approve only uncontrolled releases and change notices, in a browser |
| Air-gapped installs | Local endpoints, bundled docs, skills and suites, qualification on site, no external MCP servers |
| Snapshots | Byte identity holds only on the pinned lavapipe CI image [Mesa llvmpipe]; elsewhere ꟻLIP thresholds apply |
| Servers | `apps/mcp`, `apps/crew` and `apps/model-gateway` ship as Linux containers for x86-64 and ARM64; Proposal CI runs in microVMs |

## Interfaces with other subsystems

| To | What | Types | Phase |
| --- | --- | --- | --- |
| All tabs | The `api` catalog; sessions; boundary labels; budgets; idempotency; the error namespace and family registry; audit payloads | API method, `ApiError` | 0 |
| ING | `SourcePatch` application; `evaluate.subscribe` and `edit.stream` under `LiteralSite` overrides; `ExternalText` values returned as handles | API method | 0 |
| KLN | Admission; `Budget` and `PriorityClass`; `release_data` Acts and standing releases; context labels on writes; Proposals, risk classes and auto-merge; audit payloads; `act.*` events | `Budget`, `PriorityClass`, `Proposal` | 1 |
| KLN | `propose.change_order` under KLN's review routing; `read.search_items` serving KLN's similarity search | API method | 2 |
| KLN | `propose.mass_change` as a swarm with one work item per repository | API method, `Plan` | 3 |
| UIX | `inspect.render`, `inspect.ask_render`; `evaluate.subscribe` and `edit.stream`; `read.language_service`; `session.ask` and `session.*` events; Proposals with verifier reports and provenance; `ActPlan`s, approval requests, the three outcomes and the approval origin's rules; `session.control` | `Proposal`, `ActPlan`, `ChangeProvenance` | 1 |
| MFG | Physical-effect, `request_quote` and `publish_passport` Act kinds and plan schemas; `bench_session`; `read.machine_data`; the CAM programmer | `ActPlan` | 2 |
| ELX | `edit.stream` and `edit.apply` for layout tools; datasheet extraction, labelled `data_untrusted`; budget caps for long tool runs | API method, `Proposal` | 1 |
| ELX | `flash_device` and board `bench_session`s with Approval-verifying client flashing | `ActPlan` | 3 |
| ECO | Catalog entries for ECO's methods; `crucible:api`; Act kinds and `release_data`; `ExternalText` and instruction authority; image rules; `std::agents` and `std::explore` | Package, `ActPlan` | 1 |
| PLT | Canonical JSON; the `ApiError` shape; `Usage` as the resource record; the `PriorityClass` to pool-lane mapping | `Usage`, `ApiError`, `PriorityClass` | 0 |
| Every tab that ships a model | The training-data rule | Policy | 1 |

## Oracles

Oracles live in `oracles/agents/`, readable but never writable by agents; held-out suites and tripwires live outside it.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| AGT-O-MCP-1 | MCP, Skills and schema conformance | Tools and `structuredContent` validate; skills match manifests and only approved roles are served; hosts without extensions work; fuzzed requests yield `<family>/<code>` errors; Tasks, polling and SDK streams agree |
| AGT-O-SDK-1 | SDK, WIT and layering parity | Golden transcripts give byte-identical canonical JSON through every SDK and raw MCP; the published `crucible:api` WIT matches the Rust types and `wasm-tools component wit` parses it; no UI crate depends on `api` |
| AGT-O-OBS-1 | Observation determinism | Scene graphs and descriptions identical across platform classes; Snapshots byte-identical on the pinned image, elsewhere mean ꟻLIP at most 0.05 (target) |
| AGT-O-OBS-2 | Description integrity | Every number maps to a fact; perturbing a fact changes the text; third-party phrasing appears only as handles |
| AGT-O-OBS-3 | Query robustness | Scores agree with a labelled set of robust and fragile queries; seeded swaps report `RankSwap` with the sample; `NearTie` reaches the agent; no score claims a guarantee |
| AGT-O-API-1 | Idempotency | Injected drops and duplicates yield zero duplicate Changes or Acts |
| AGT-O-API-2 | Concurrency and drag streams | A TLA+ model checks; multi-writer tests lose no update and catch every stale base; an `edit.stream` ends in one Change, and no overridden result is shared |
| AGT-O-POL-1 | Policy enforcement | A reference evaluator agrees with the server over scopes, methods, protection, labels, clearances, chains of depth 1 to 3, the signature table, review routing and every forbidden action under break-glass |
| AGT-O-POL-2 | Delegation grants | Exchange without a live grant, for non-agent scopes, or for Approvals or `policy:admin` is refused; tokens are sender-constrained |
| AGT-O-INJ-1 | Injection resistance | Zero attacker-chosen consequential actions via doc comments, identifiers, templates, textures or a host with a fetch tool. Part names, BOM text, notes, diagnostics and embossed text reach clean contexts only as handles, even after a human merge. A host with a shell tool that runs the CLI and an editor extension achieves no merge, endorsement, waiver, local export or trusted span. A crew context cannot leak a bit through the choice or timing of fetches. Write-down and label laundering count as successes |
| AGT-O-LABEL-1 | Clearance and write-down | Tripwires never reach uncleared contexts or lower-labelled repositories; undeclassified writes down fail; `Declared` clients get nothing above `internal` and nothing scoped or licence-restricted, and new ones start at `public`. An attested host with a fetch tool is never clean, so its Proposals are at least R2. A tainted edit to a clean branch succeeds at R3; endorsement changes integrity without declassification. Concurrent grants, re-authorization and stdio relaunch keep the label; only `session.reset_context` clears it |
| AGT-O-RISK-1 | Risk classes and auto-merge | A labelled corpus gets the expected classes: loosening, waivers and tainted changes are R3 or higher; no `data_untrusted` change is R1; external-host Proposals are at least R2; a clean R1-shaped change on an assembly with a merged supplier part is R1. Auto-merge refuses everything outside policy |
| AGT-O-VER-1 | Verifier efficacy | The planted-defect catch rate meets its target; reviews from the author's delegating human in an unattested host are marked `Declared` |
| AGT-O-PROV-1 | Provenance | Every Change carries a valid signed statement with complete fields, including the endpoint record; tampering is detected; every crew call has a replay record |
| AGT-O-BUD-1 | Budgets, rate limits and priority | Spend never exceeds a cap by more than one safe-point interval; limits and fair shares hold; declared tokens are never enforced; every class runs on its pool lane |
| AGT-O-SWARM-1 | Plans, leases and mass changes | Invalid generated plans are rejected and valid ones pass; stale-lease writes are always rejected; held-out grading is unreadable by workers; a mass change over seeded repositories releases only when every Proposal passes |
| AGT-O-EXP-1 | Exploration | Hypervolume within 5% of the references (target); equal seeds give identical synchronous sequences; failures counted |
| AGT-O-ACT-1 | Act integrity | Unapproved commits, changed plans, replays, forwarded links, author-chosen names, hidden characters, approval spam across sessions and chain-internal approvals where the table forbids them are refused. Return for changes allows an immediately changed plan and refuses the same digest; deny as suspicious freezes and blocks for 24 h. Unenrolled, synced or day-old credentials, scripted main-origin pages and tossed cookies cannot approve. Swapped firmware, Material versions or documents fail with `act/subject_mismatch`. The page renders every physical-effect kind, and signed Approvals verify offline |
| AGT-O-EXIT-1 | Data release | Every egress path runs the stage, and local writes only within their exemption; failing recipients, scoped or licence-restricted payloads and a party listed the day before are refused; recipient changes show the banner; standing releases refuse over-ceiling or off-schema payloads |
| AGT-O-SAFE-1 | Physical safety | Under wire capture against real servers or simulators (OctoPrint, Moonraker with Klipper, PrusaLink, URSim, controller simulators), no transfer carries a start semantic and every device stays idle. No plan schema expresses a start, and only allowlisted OPC UA methods are called. `start_print` without a site safety record, extrusion or a printer-side confirmation within 10 minutes is refused; `flash_device` leaves the target held; a flash from the main web origin is impossible; `run_rig_test` needs `unattended_safe` |
| AGT-O-SAFE-2 | Bench sessions | Transfers beyond the count, outside the lineage, after the expiry or after a hazard change are refused; agents cannot open or extend a session; every transfer keeps its read-back, hold and hash checks and appears on the page afterwards |
| AGT-O-AUDIT-1 | Audit | One entry per call in KLN's log; no entry holds labelled bytes; shredding an identity key leaves the log verifiable and the person unidentifiable |
| AGT-O-BENCH-1 | Agent quality gate | Golden tasks and the held-out set meet the regression thresholds per release and endpoint |
| AGT-O-DATA-1 | Training data | Eligibility follows labels, licences and per-item proof; canaries are not extractable; withdrawals complete within 30 days |
| AGT-O-DOCS-1 | Docs | Every example builds and its checks pass; every public std item has a doc comment, an example and units |

## Phasing

No AGT capability is in contract 13.4's tables; each row follows its owner's phase for what it rests on. The phase 0 gate's freedom-to-operate search covers this tab's Proposal and review flow (contract 13.1).

| Phase | AGT contribution to the gate |
| --- | --- |
| 0 | `api-schema` and `api` in single-principal mode; Session, Read, Edit and core Evaluate methods; idempotency; the error namespace and the docs pipeline; the MCP server on stdio and HTTP; the Rust SDK; source-level descriptions. AGT-O-MCP-1, SDK-1, OBS-2, API-1, API-2 and DOCS-1 green |
| 1 | GP1 and GP2 worked by agents through external MCP hosts: enforcement of scopes, labels, budgets and approvals; device agents for local credentials; Inspect, Compare, Propose, CI reports and risk classes; context labels and resets; drag streams; `crucible:api`; release and export Acts on the approval origin with the three outcomes, used in the physical dry run (contract 13.2, chain D); the Python SDK; three roles. The golden-task harness, injection suite and qualification run on at least two endpoints and report pass^1 and pass^4. AGT-O-POL-1, INJ-1, ACT-1, RISK-1, LABEL-1, AUDIT-1 and EXIT-1 green |
| 2 | Hosted crew, delegation grants, model gateway with its taint check, and extraction; the TypeScript SDK; nine further roles; swarms; exploration; auto-merge; review routing for change orders; standing releases; physical-effect and remaining data-release Acts; bench sessions. Swarm tasks on GP3 and GP4 beat the single-agent baseline at no more than 3× its cost (target); AGT-O-SAFE-1, SAFE-2 and POL-2 green |
| 3 | Mass change; hypervolume knowledge gradient; training opt-in with canary tests; a public bounty; an interpreter evaluated for `instruction_tainted` roles; `publish_passport`; `flash_device`; watermark and expiry on data release. Golden tasks on GP5 report pass^1 and pass^4 on every qualified endpoint |
| 4 | Validation against physical test data with correlation checks. GP6 explorations confirm at least 3 Pareto-optimal variants at `SignOff` (target) |
| 5 and later | A compliance-evidence role |

## Open questions

1. **R1 thresholds.** Are a 90% margin floor, a 0.5 mm geometry deviation and a 1% cost increase the right defaults for R1 and auto-merge? They wait on review data from the first organizations that enable auto-merge in phase 2.

## Contract change requests

- **CCR-AGT-14. Single-person merge approvals.** Contract 5.4's merge-approval row forbids the author and the delegating human from approving a merge into a protected branch. Single-person mode covers only the two-person rows, so an organization with one eligible person can never merge its agents' Proposals into a protected `main`. Proposed: single-person mode also covers the merge-approval row. The one person approves with a fresh approval credential after an `Attested` verifier review, the record is marked `single_person`, and R3 and R4 merges take effect after the mode's 72-hour delay.

## Sources

| Key | Title | URL | Date opened |
| --- | --- | --- | --- |
| [15 CFR 734.18] | 15 CFR 734.18, activities that are not exports (eCFR) | https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734/section-734.18 and Cornell LII: https://www.law.cornell.edu/cfr/text/15/734.18 | By 2026-10-11 |
| [22 CFR 120.54] | 22 CFR 120.54, paragraphs (a)(5) and (b), Cornell LII | https://www.law.cornell.edu/cfr/text/22/120.54 | By 2026-10-11 |
| [22 CFR 120.54 eCFR] | 22 CFR 120.54, activities that are not exports (eCFR) | https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54 | By 2026-10-11 |
| [22 CFR 120.56] | 22 CFR 120.56, release, Cornell LII | https://www.law.cornell.edu/cfr/text/22/120.56 | By 2026-10-11 |
| [A2A specification] | A2A Protocol specification (version 1.0.0) | https://a2a-protocol.org/latest/specification/ | By 2026-10-11 |
| [ABC dataset] | ABC dataset | https://deep-geometry.github.io/abc-dataset/ | By 2026-10-11 |
| [Alrashedy et al. 2024] | Alrashedy et al., "Generating CAD Code with Vision-Language Models for 3D Designs" (CADPrompt, CADCodeVerify; arXiv:2410.05340) | https://arxiv.org/abs/2410.05340 | By 2026-10-11 |
| [Ament et al. 2023] | Ament et al., "Unexpected Improvements to Expected Improvement for Bayesian Optimization" (arXiv:2310.20708) | https://arxiv.org/abs/2310.20708 | By 2026-10-11 |
| [Anthropic effective agents] | Anthropic, "Building effective agents" | https://www.anthropic.com/engineering/building-effective-agents | By 2026-10-11 |
| [Anthropic multi-agent research] | Anthropic, "How we built our multi-agent research system" | https://www.anthropic.com/engineering/multi-agent-research-system | By 2026-10-11 |
| [Anthropic writing tools] | Anthropic, "Writing effective tools for agents" | https://www.anthropic.com/engineering/writing-tools-for-agents | By 2026-10-11 |
| [Apple passkeys] | Apple Developer, "Supporting passkeys" | https://developer.apple.com/tutorials/data/documentation/authenticationservices/supporting-passkeys.json | By 2026-10-11 |
| [Autodesk Fusion Data MCP] | Autodesk, "Introducing the Autodesk Fusion Data MCP Server" | https://www.autodesk.com/products/fusion-360/blog/introducing-the-autodesk-fusion-data-mcp-server/ | By 2026-10-11 |
| [Autodesk Fusion MCP] | Autodesk, "Introducing the Fusion MCP" | https://www.autodesk.com/products/fusion-360/blog/introducing-the-fusion-mcp-opening-fusion-to-ai-powered-workflows/ | By 2026-10-11 |
| [BetrVG section 87] | Works Constitution Act (Betriebsverfassungsgesetz), English translation, section 87 | https://www.gesetze-im-internet.de/englisch_betrvg/englisch_betrvg.html | By 2026-10-11 |
| [Beurer-Kellner et al. 2025] | Beurer-Kellner et al., "Design Patterns for Securing LLM Agents against Prompt Injections" (arXiv:2506.08837) | https://arxiv.org/abs/2506.08837 and https://arxiv.org/pdf/2506.08837v3 | By 2026-10-11 |
| [BoTorch introduction] | BoTorch documentation, introduction | https://botorch.org/docs/introduction | By 2026-10-11 |
| [BoTorch multi-objective] | BoTorch documentation, multi-objective optimization (v0.18.1) | https://botorch.org/docs/multi_objective | By 2026-10-11 |
| [Claude tool definitions] | Claude API, "Define tools" (tool `name` must match `^[a-zA-Z0-9_-]{1,128}$`) | https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools | By 2026-10-11 |
| [CloudNC CAM Assist] | CloudNC, "What to see at IMTS 2026" | https://www.cloudnc.com/blog/what-to-see-at-imts-2026-ai-assisted-cnc-programming-and-where-to-find-cloudnc | By 2026-10-11 |
| [Daulton et al. 2023] | Daulton, Balandat and Bakshy, "Hypervolume Knowledge Gradient" (ICML 2023) | https://proceedings.mlr.press/v202/daulton23a.html | By 2026-10-11 |
| [DE247 NX Copilot] | Digital Engineering 24/7, "Siemens Brings AI Copilot, Immersive Design to NX" | https://www.digitalengineering247.com/article/siemens-brings-ai-copilot-immersive-design-to-nx | 2026-10-12 |
| [Debenedetti et al. 2024] | Debenedetti et al., "AgentDojo" (arXiv:2406.13352) | https://arxiv.org/abs/2406.13352 | By 2026-10-11 |
| [Debenedetti et al. 2025] | Debenedetti et al., "Defeating Prompt Injections by Design" (CaMeL; arXiv:2503.18813) | https://arxiv.org/abs/2503.18813 | By 2026-10-11 |
| [DeepCAD README] | DeepCAD repository README ("parsed from Onshape public documents with links from ABC dataset") | https://github.com/ChrisWu1997/DeepCAD | By 2026-10-11 |
| [Dong et al. 2026] | Dong, Li and Wu, "MUSE" (arXiv:2605.28579) | https://www.alphaxiv.org/abs/2605.28579 | By 2026-10-11 |
| [Epoch CadEval] | Epoch AI, CadEval | https://epoch.ai/benchmarks/cad-eval | By 2026-10-11 |
| [Fusion 360 Gallery licence] | Fusion 360 Gallery Dataset license | https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md and https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/LICENSE.md | By 2026-10-11 |
| [GDPR Article 17] | GDPR Article 17, right to erasure | https://gdpr-info.eu/art-17-gdpr/ | By 2026-10-11 |
| [Ghodsi et al. 2011] | Ghodsi et al., "Dominant Resource Fairness: Fair Allocation of Multiple Resource Types" (NSDI 2011) | https://www.usenix.org/legacy/event/nsdi11/tech/full_papers/Ghodsi.pdf | By 2026-10-11 |
| [Hvarfner et al. 2024] | Hvarfner, Hellsten and Nardi, "Vanilla Bayesian Optimization Performs Great in High Dimensions" (arXiv:2402.02229) | https://arxiv.org/abs/2402.02229 | By 2026-10-11 |
| [IETF Idempotency-Key] | IETF draft, "The Idempotency-Key HTTP Header Field" (draft-07, expired) | https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/ | By 2026-10-11 |
| [in-toto Statement] | in-toto Attestation Framework, Statement v1 | https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md | By 2026-10-11 |
| [ITA Consolidated Screening List] | US International Trade Administration, Consolidated Screening List | https://www.trade.gov/consolidated-screening-list | By 2026-10-11 |
| [Mallis et al. 2026] | Mallis et al., "Text-to-CAD Evaluation with CADTests" (arXiv:2605.07807) | https://arxiv.org/abs/2605.07807 | By 2026-10-11 |
| [MCP Apps] | MCP Apps extension | https://modelcontextprotocol.io/extensions/apps/overview.md | By 2026-10-11 |
| [MCP authorization] | MCP 2026-07-28, Authorization | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/index.md | By 2026-10-11 |
| [MCP authorization security] | MCP 2026-07-28, Authorization security considerations (localhost redirect URI risks) | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations | By 2026-10-11 |
| [MCP changelog] | MCP 2026-07-28 changelog | https://modelcontextprotocol.io/specification/2026-07-28/changelog | By 2026-10-11 |
| [MCP elicitation] | MCP 2026-07-28, Elicitation (URL mode and phishing) | https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation | By 2026-10-11 |
| [MCP MRTR] | MCP 2026-07-28, Multi Round-Trip Requests | https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr.md | By 2026-10-11 |
| [MCP Rust SDK] | Official Rust SDK for MCP (`rmcp`) | https://github.com/modelcontextprotocol/rust-sdk | By 2026-10-11 |
| [MCP security practices] | MCP Security Best Practices (2026-07-28) | https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices.md | By 2026-10-11 |
| [MCP Skills] | MCP Skills extension | https://modelcontextprotocol.io/extensions/skills/overview.md | By 2026-10-11 |
| [MCP specification] | MCP Specification, latest revision (2026-07-28) | https://modelcontextprotocol.io/specification/latest | By 2026-10-11 |
| [MCP Tasks] | MCP Tasks extension | https://modelcontextprotocol.io/extensions/tasks/overview.md | By 2026-10-11 |
| [MCP tools] | MCP 2026-07-28, Tools | https://modelcontextprotocol.io/specification/2026-07-28/server/tools.md | By 2026-10-11 |
| [MDN Set-Cookie] | MDN Web Docs, Set-Cookie header (cookie prefixes) | https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie | 2026-10-12 |
| [Mesa llvmpipe] | Mesa documentation, LLVMpipe | https://docs.mesa3d.org/drivers/llvmpipe.html | By 2026-10-11 |
| [Meta Rule of Two] | Meta AI, "Agents Rule of Two" | https://ai.meta.com/blog/practical-ai-agent-security/ | By 2026-10-11 |
| [Microsoft FIDES] | Microsoft Agent Framework, "FIDES" | https://devblogs.microsoft.com/agent-framework/fides/ | By 2026-10-11 |
| [NVIDIA FLIP] | Ebelin et al., "ꟻLIP: A Difference Evaluator for Alternating Images" (High Performance Graphics 2020) | https://research.nvidia.com/labs/rtr/publication/andersson2020flip/ | By 2026-10-11 |
| [Onshape FeatureScript MCP] | Onshape, "FeatureScript MCP Server Enables Text Code CAD" | https://www.onshape.com/en/blog/featurescript-mcp-server-enables-text-code-cad | 2026-10-12 |
| [Onshape terms] | Onshape Terms of Use | https://www.onshape.com/en/legal/terms-of-use | By 2026-10-11 |
| [OPC 10031-4] | OPC Foundation, OPC 10031-4 (OPC UA for ISA-95, Part 4: Job Control) v2.00, section 6.3 | https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3 | By 2026-10-11 |
| [OpenID Connect Core] | OpenID Connect Core 1.0, section 9, client authentication (`private_key_jwt`) | https://openid.net/specs/openid-connect-core-1_0.html | By 2026-10-11 |
| [OWASP agentic top 10] | OWASP Top 10 for Agentic Applications for 2026 (resource page, published 9 December 2025) | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ ; item list as reproduced at https://docs.modulos.ai/frameworks/owasp-top-10-agentic | By 2026-10-11 |
| [OWASP LLM01] | OWASP, "LLM01:2025 Prompt Injection" | https://genai.owasp.org/llmrisk/llm01-prompt-injection/ | By 2026-10-11 |
| [pymoo algorithms] | pymoo algorithm list (0.6.2) | https://pymoo.org/algorithms/list.html | By 2026-10-11 |
| [RFC 8693] | RFC 8693, "OAuth 2.0 Token Exchange" | https://www.rfc-editor.org/rfc/rfc8693.html | By 2026-10-11 |
| [RFC 9449] | RFC 9449, "OAuth 2.0 Demonstrating Proof of Possession (DPoP)" | https://www.rfc-editor.org/rfc/rfc9449.html | By 2026-10-11 |
| [RFC 9457] | RFC 9457, "Problem Details for HTTP APIs" | https://www.rfc-editor.org/rfc/rfc9457.html | By 2026-10-11 |
| [Rukhovich et al. 2024] | Rukhovich et al., "CAD-Recode" (arXiv:2412.14042) | https://arxiv.org/abs/2412.14042 | By 2026-10-11 |
| [Siemens NX Copilot tips] | Siemens Designcenter blog, Designcenter X NX Copilot tips (post 13115) | https://blogs.sw.siemens.com/designcenter/wp-json/wp/v2/posts/13115 | By 2026-10-11 |
| [SolidCraft repository] | SolidCraft (solvecraft) repository README | https://github.com/bherbruck/solvecraft | 2026-10-12 |
| [W3C WebAuthn Level 3] | W3C, "Web Authentication: An API for accessing Public Key Credentials, Level 3" (Recommendation, 25 August 2026) | https://www.w3.org/TR/webauthn-3/ | By 2026-10-11 |
| [Wang et al. 2026] | Wang et al., "Text2CAD-Bench" (arXiv:2605.18430) | https://arxiv.org/abs/2605.18430 and https://arxiv.org/pdf/2605.18430 | By 2026-10-11 |
| [WIT specification] | WebAssembly Component Model, WIT format | https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md | 2026-10-12 |
| [Yang et al. 2023] | Yang et al., "Set-of-Mark Prompting" (arXiv:2310.11441) | https://arxiv.org/abs/2310.11441 | By 2026-10-11 |
| [Yao et al. 2024] | Yao et al., "τ-bench" (arXiv:2406.12045) | https://arxiv.org/abs/2406.12045 | By 2026-10-11 |
| [Zoo Zookeeper] | Zoo, "Announcing Zookeeper, Our Conversational CAD Agent" | https://zoo.dev/blog/announcing-zookeeper | 2026-10-12 |
| [Zoo Zookeeper research] | Zoo, Zookeeper research | https://zoo.dev/research/zookeeper | By 2026-10-11 |
