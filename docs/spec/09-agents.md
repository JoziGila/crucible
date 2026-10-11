# Agents (AGT)

Agents use the same typed `api` as people: one catalog of API methods in eight groups, served over MCP 2026-07-28 and native Rust, Python and TypeScript SDKs. Agents edit only branches and deliver Proposals that build, pass every check, carry signed provenance and survive an independent verifier. The server, not the model, enforces safety: every model context carries a label, untrusted text never gains instruction authority, and every effect outside Crucible waits for an assigned human to approve its exact plan.

## Scope and invariants

This tab owns the `api` crate (catalog, transports, sessions, labels at the boundary, budgets, errors, audit entries and Acts) and specifies observation, roles, swarms, Proposals, model independence, benchmarks, training data and agent-facing docs. Kiln, `repo`, Anvil, Flux and PLT own the machinery underneath.

1. **Parity of capability.** People, agents, the UI, the CLI and CI call the same methods. Authority differs on purpose: only accountable humans approve Acts, protected merges and policy.
2. **Branch confinement.** Agents write only to unprotected branches; protected branches change only through Proposals.
3. **Proposals are the unit of agent work.** A Proposal enters review only after it builds, passes every check and carries server-generated snapshots.
4. **Enforcement lives in the server.** `api` checks scopes, budgets, labels and approvals on every call, whatever model or host drives the agent.
5. **No correctness depends on a model.** Every agent output becomes Ingot source or a typed record that deterministic checks verify.
6. **Every claim has an oracle.** Exit criteria are checks, and graders live in `oracles/agents/`, which agents can read but never write.

| Term | Meaning |
| --- | --- |
| Session | A server-minted handle binding a principal, a branch, a grant, a budget and a model context |
| Model context | The unit that accumulates a label (contract section 7.6): a hosted-crew conversation, or an external host's OAuth token family |
| Role | An Ingot record plus a skill: purpose, scopes, write-set rule, exit checks and outputs |
| Delegation grant | A signed, time-bound grant from a human to agents: scopes, repository, budget, expiry |
| Risk class | R0 to R4, computed by the server from a Proposal's semantic diff and the labels of its authoring contexts |

"Evaluation" always means a Kiln request, so measuring agents is called benchmarking here.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Parity of capability | Every UI, CLI, CI and agent action is an API method; tool lists differ only by grant | A missing method fails the catalog coverage test | AGT-O-2 | 0 |
| Branch confinement | Agent sessions open only on unprotected branches | `session.branch_protected` | AGT-O-7 | 0 |
| Server-side enforcement | Scopes, labels, budgets and approvals checked on every call | Typed `auth`, `label` and `budget` errors | AGT-O-7 | 0 |
| Checked outputs | Agent output lands as Ingot or typed records that checks verify | `edit.introduces_errors`, `propose.preconditions_failed` | AGT-O-15 | 1 |

## The `api` surface

### One catalog, several transports

**Decision D-AGT-1:** The `api` method catalog is the only programmatic surface of Crucible; MCP tools, SDK methods, UI commands and CLI subcommands map one-to-one onto API methods. *Why:* agents are first-class users, a second surface would drift from the first, and principle 1 forbids privileged paths. *Rejected:* a separate agent API (drifts and doubles testing); a code-only surface that runs scripts (loses typed inspection, evaluation and review).

`core/api` holds method types, dispatch, policy enforcement, labels, budgets, the idempotency store and audit entries, and no transport code. The desktop app, web app and CLI link it in process. `apps/mcp` serves it over stdio and Streamable HTTP on the official Rust SDK, `rmcp`, which implements 2026-07-28 and stays compatible with 2025-11-25 [S10]; `apps/crew`, the hosted crew (phase 2), reaches Crucible only through the public SDK.

### MCP profile

MCP 2026-07-28 removes protocol-level sessions, so every request carries its version and client capabilities in `_meta`, and servers that need state mint explicit handles [S1][S2][S3]. It replaces server-initiated requests with Multi Round-Trip Requests (MRTR), moves Tasks into an extension, and deprecates Roots, Sampling and Logging [S2].

**Decision D-AGT-2:** Crucible targets MCP 2026-07-28 with the Tasks and Skills extensions. It serves 2025-11-25 clients for at least twelve months after phase 1 and uses no deprecated MCP capability. *Why:* stateless requests let team servers scale horizontally without sticky sessions, and deprecated capabilities have a removal window of at least twelve months [S2]. *Rejected:* a custom agent protocol (no host ecosystem); building on 2025-11-25 (needs session affinity and is superseded).

| MCP element | Crucible use |
| --- | --- |
| `server/discover` | Versions, extensions, catalog version, and server instructions stating the external-text rule (D-AGT-25) [S2][S4][S8] |
| `tools/list` | One tool per method the caller's grant allows, in deterministic order; the list may vary by authorization, never by connection [S3] |
| `tools/call` | `outputSchema` and `structuredContent` on every tool; domain failures as tool execution errors [S3] |
| Resources | Change-addressed `crucible://` URIs with long `ttlMs` and `cacheScope: "private"` [S2] |
| `subscriptions/listen` | Branch-head, Proposal and Evaluation resources and `toolsListChanged` [S2] |
| Tasks extension | Long Evaluations return tasks, driven by `tasks/get`, `tasks/update` and `tasks/cancel` [S4] |
| MRTR | `act.commit` returns `act.approval_pending` with a request id, never a URL (D-AGT-20); step-up uses `insufficient_scope` [S5][S6] |
| Skills extension | Role skills with SHA-256 manifests; `apps/mcp` implements `skills/list`, `skills/get` and the manifests itself, because the `rmcp` README does not list Skills [S8][S10] |
| Apps extension | A read-only Proposal viewer (phase 2) that never approves anything [S9] |
| HTTP headers | Gateways rate-limit on `Mcp-Method` and `Mcp-Name`; `x-mcp-header` mirrors only `shard_key` [S3] |
| Not used | Sampling, Roots, Logging and HTTP+SSE [S2] |

`shard_key` is HMAC-SHA-256 of the repository id under the tenant's routing key, truncated to 16 bytes, because mirrored headers are visible to network intermediaries [S3] and repository names reveal programmes. `requestState` is sealed with AEAD and bound to the principal, a digest of the original request and a 15-minute expiry, as the spec requires when it affects authorization [S5]. `edit.apply` becomes the tool `edit_apply`, since some model APIs restrict tool names [unverified for every provider].

Hosts must treat tool annotations and skill content as untrusted [S3][S8]. Crucible's trust in approved role skills binds only the hosted crew.

### Sessions, identity and delegation

A principal is a person (`user:<id>`), an agent instance (`agent:<org>/<role>/<instance>`) or a service (`service:<name>`); an agent always acts for a human. The delegation chain has the delegating human at index 0 and the current actor last. The server derives it from its own session lineage, never from token `act` claims, which RFC 8693 makes informational for nested actors [S47].

Remote transports use OAuth 2.1 as MCP specifies: protected resource metadata, resource indicators, audience-bound tokens, step-up through `insufficient_scope`, and Client ID Metadata Documents for registration [S2][S6].

**Decision D-AGT-3:** A Session is an opaque 128-bit random handle that the server binds to the authenticated principal and token issuer. It expires after 24 hours idle or 7 days total by default. Atomicity is per Change, isolation is per branch, and there is no long-lived transaction object. *Why:* MCP 2026-07-28 has no protocol sessions and recommends explicit handles [S3]; possession of a handle never counts as authentication [S7]; cheap branches already isolate work. *Rejected:* protocol-level sessions (removed from MCP); multi-call transactions with locks (contention, leaked locks, a second concept beside branches).

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
    pub context: Labels,                 // the model context's current label (D-AGT-24)
}
```

The effective grant intersects the delegating human's permissions, the role's scopes, the repository policy and the request. Clearance is the meet of the human's clearance, the client's or endpoint's clearance (D-AGT-19) and the repository policy.

**Decision D-AGT-28:** Agents act under delegation grants: signed, time-bound records that a human creates, naming scopes, repository, budget and expiry. The hosted crew may exchange tokens only against a live grant and only for agent scopes. Tokens are sender-constrained by DPoP or mTLS, crew instances run per tenant, and Approvals and `policy:admin` are never obtainable by exchange. *Why:* a crew that mints tokens for everyone who ever delegated turns one compromise of `apps/crew` into authority over every user (R5-45); DPoP binds tokens to a key the client holds [S58]. *Rejected:* standing token exchange; bearer tokens for crew workers.

Only the delegating human steers a running agent, through `session.control`. An @mention by anyone else creates a request in the delegating human's inbox, and attachments enter the context as `ExternalText`, never as goal text.

### Changes, branches and concurrency

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
    RenameSymbol { symbol: SymbolPath, to: Ident },          // writes #[was(old)]
    AddCheck { target: FeaturePath, predicate: IngotExpr, severity: Severity },
    SetMaterial { part: FeaturePath, material: MaterialRef },
    AddDependency { package: PackageName, version: VersionReq },
    CreateFile { path: SourcePath, contents: String },
    DeleteFile { path: SourcePath, expected: Sha256 },
}

pub enum ParamValue { Expr(IngotExpr), FromRef(ValueRef) }   // FromRef cites an untrusted value (D-AGT-24)
```

The response, `EditsApplied`, carries the new `ChangeId`, any rebase, the formatted `SourcePatch`es, compiler diagnostics, a semantic diff summary and usage.

**Decision D-AGT-4:** Structured edits are a convenience layer that lowers to Ingot source patches; the formatter normalizes touched regions, and the response returns the patch. *Why:* one model, three editors; reviewers and agents read the same Ingot whatever produced it. *Rejected:* edits on geometry or on an opaque feature tree (nothing exists only outside Ingot).

Compile errors fail with `edit.introduces_errors` unless `allow_errors` is set on the agent's own branch. A stale `Patch` fails with `edit.patch_mismatch`, an edit outside the write set with `edit.write_set_violation`, and every write carries the context's label.

**Decision D-AGT-5:** Concurrency control is optimistic: every mutating call names its base Change. On a stale base the server rebases only when `repo`'s semantic merge reports no overlap in touched files, features, parameters or entities, and it reports the rebase. *Why:* explicit over magic; agents need to know their view was stale. *Rejected:* pessimistic locks (deadlocks, abandoned locks from crashed agents); silent rebase (hides semantic interference).

One call is one Change, a Proposal merge is one Change, and a swarm's parent Proposal merges all its children at once. On a shared live branch (phase 2, with KLN's live documents) an agent's Change enters the CRDT as one batch.

### Idempotency and retries

MCP 2026-07-28 removed stream resumability, so a broken stream loses the in-flight request and the client re-issues it [S2]. A retried mutation must not apply twice.

**Decision D-AGT-6:** Every method that changes state or spends budget requires an idempotency key, a client-generated 128-bit random value. The server stores (principal, method, key) with a SHA-256 fingerprint of the canonical arguments and the response for 24 hours. *Why:* exactly-once effects under routine retries. *Rejected:* best-effort deduplication by argument hash (merges legitimately repeated calls); relying on transport resumability (removed from MCP).

| Situation | Behavior |
| --- | --- |
| Same key and fingerprint, completed | The stored response, marked `replayed: true` |
| Same key and fingerprint, running | `request.in_flight` with `retry_after_ms` |
| Same key, different fingerprint | `request.idempotency_mismatch`, naming the original call |
| Key older than 24 hours | Treated as new, with a notice |

The SDKs generate keys and retry transport failures with the same key, using capped exponential backoff with jitter.

### Evaluations and streaming results

Builds, checks, simulations, manufacturing plans, costing and explorations run as Evaluations on Kiln. An Evaluation moves through `queued`, `running`, `done` and `aborted` (contract section 2), mapped to the MCP task states `working`, `completed`, and `cancelled` or `failed` [S4].

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

A long Evaluation returns a task when the client declared the Tasks extension; otherwise the call waits up to `wait_ms` and returns an id for `evaluate.get` [S4]. Cancellation is an Abort (contract section 7.2): nodes that finished keep their results, nodes that observed it write nothing, and the final frame lists what completed.

### Budgets, limits and admission

AGT defines the fields of `Budget` and `PriorityClass`, which live in `base` so that Kiln never depends on `api`; PLT adopts `Usage` as its resource record.

```rust
pub struct Budget {
    pub money: Option<Money>,            // base Money { amount: Decimal, currency }
    pub core_seconds: Option<u64>,
    pub gpu_seconds: Option<u64>,
    pub model_tokens: Option<u64>,       // hosted crew only
    pub wall_clock: Option<Duration>,
    pub max_evaluations: Option<u32>,
}

pub struct Usage {
    pub core_seconds: u64, pub gpu_seconds: Option<u64>, // None when a shared GPU was unattributed
    pub memory_gb_seconds: u64, pub cas_bytes_written: u64,
    pub model_input_tokens: u64, pub model_output_tokens: u64, pub cost: Money,
}
```

Budgets nest: organization, project, Proposal tree, work item, session. Policy sets ceilings per session (default 25 USD), Proposal tree (200 USD) and day (1,000 USD), and raising one is audited.

**Decision D-AGT-29:** Admission reserves the priced upper bound of each Evaluation's work, never a mean estimate. Every Op whose estimate exceeds 10 core-seconds takes a deterministic work budget (fuel or iteration cap) derived from the remaining money budget and reaches a safe point at least every 10 core-seconds; exhausting it is a budget Abort that keeps the last checkpoint. *Why:* adaptive solves, certified geometry and Wasm components vary in cost by orders of magnitude at one input size, so regression means cannot bound spend (R6-29). *Rejected:* regression estimates as reservations; caps enforced only between Ops, which an unbounded factorization overruns.

The work budget never enters an `OpKey`: an Op either completes with its usual value or aborts and writes nothing. GPU seconds come from timestamp queries on compute-only submissions and are unattributed when the renderer shares the device.

A failed reservation returns `budget.exceeded` before any work, with cheaper options as fixes. Sessions get a warning frame at 80% of a cap, and running Evaluations abort at the cap. An anomaly alert fires within a minute when a session spends three times the median for its role and task size.

| Method class | Default sustained rate | Burst |
| --- | --- | --- |
| Read, Inspect except snapshots | 50 per second | 200 |
| `inspect.render`, `inspect.section`, `inspect.ask_render` | 4 concurrent | — |
| Edit | 10 per second | 30 |
| Starting Evaluations | 5 per second | 20 |
| Propose | 1 per second | 10 |
| `act.prepare` | 10 per hour; at most 3 pending approval requests | — |

Limits are per principal at the gateway: HTTP 429 or `limit.rate`, each with a retry delay. Responses default to concise detail, which uses about a third of the tokens [S31], and results above 20,000 tokens are truncated with a cursor, below Claude Code's 25,000-token tool-response limit [S31].

### Errors as guidance

```rust
pub struct ApiError {
    pub code: ErrorCode,                 // stable, e.g. "edit.stale_base"
    pub r#type: Uri,                     // crucible://errors/edit.stale_base
    pub title: String,
    pub detail: String,                  // external strings only as handles
    pub status: u16,
    pub instance: Uri,                   // this occurrence's audit entry
    pub retry: Retry,                    // Never | After(ms) | AfterChange
    pub fixes: Vec<SuggestedFix>,        // ApplyEdits | Call | Read | AskHuman, most likely first
    pub context: serde_json::Value,      // schema in the error catalog
}
```

**Decision D-AGT-7:** Every failure is an `ApiError` shaped like RFC 9457 Problem Details with typed context and ordered suggested fixes, many machine-applicable. Domain failures are MCP tool execution errors, not JSON-RPC protocol errors. *Why:* RFC 9457 is the standard machine-readable error format [S45]; MCP advises giving tool execution errors to the model so it can self-correct [S3]. *Rejected:* free-text errors (agents cannot act on them reliably); JSON-RPC errors for domain failures (models recover poorly from them [S3]).

Compiler diagnostics and `ResolveError`s arrive in `context` with their own fixes. A fix produced by third-party code carries `data_untrusted` and may not add dependencies or touch checks, tolerances, policy files or protected paths.

| Family | Representative codes | Typical fix |
| --- | --- | --- |
| `auth` | `scope_denied`, `step_up_required`, `no_live_grant` | Step-up; ask the delegating human for a grant |
| `session` | `expired`, `branch_protected`, `lease_lost` | Open a session; fork a branch |
| `edit` | `stale_base`, `patch_mismatch`, `introduces_errors`, `write_set_violation`, `protected_path` | Re-read and retry; apply the compiler's fix |
| `query` | `resolve_failed`, `no_robust_candidate` | Pin a candidate; `inspect.suggest_query` |
| `budget`, `limit` | `exceeded`, `rate` | Lower fidelity; wait |
| `propose` | `preconditions_failed`, `policy_unsatisfied`, `self_review_forbidden` | The failing checks and missing approvals |
| `act` | `approval_pending`, `plan_changed`, `recipient_unverified`, `onsite_required`, `denied_cooldown` | Wait for the assigned approver; prepare again |
| `label` | `write_down`, `exceeds_clearance`, `client_unattested`, `raw_external_forbidden` | A new context; a cleared endpoint; a declassification |

### Native SDKs

Rust types in `core/api` are the single source of truth. A build step emits JSON Schema 2020-12, which MCP accepts in full [S2], and generates the MCP tool definitions and the Python and TypeScript SDKs; the SDK version equals the catalog version. Rust and Python ship in phase 1 and TypeScript in phase 2 (contract section 13.2), and golden transcripts must give byte-identical canonical JSON through every SDK and raw MCP.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| MCP server | 2026-07-28 with Tasks and Skills; 2025-11-25 for twelve months after phase 1 | Unsupported version returns the supported list | AGT-O-1 | 0 |
| Skills serving | `skills/list`, `skills/get` and manifests in `apps/mcp` | Manifest mismatch refuses the skill | AGT-O-1 | 1 |
| Sessions and delegation | Handle bound to principal and issuer; chain from server lineage | `session.expired`, `auth.scope_denied` | AGT-O-7 | 0 |
| Delegation grants | Crew token exchange only against a live grant; DPoP or mTLS | `auth.no_live_grant` | AGT-O-24 | 2 |
| Structured edits | Lower to `SourcePatch`; atomic per call; handle-cited values | `edit.*` errors with fixes | AGT-O-6 | 0 |
| Optimistic concurrency | Exact base; rebase only when disjoint | `edit.stale_base` | AGT-O-6 | 0 |
| Idempotency | Keys with fingerprints kept 24 h | `request.idempotency_mismatch` | AGT-O-5 | 0 |
| Evaluation streams | Frames over Tasks, polling and SDK streams; identical final results | Abort lists completed nodes | AGT-O-1 | 0 |
| Admission and metering | Priced upper-bound reservations; safe points every 10 core-seconds | `budget.exceeded`; budget Abort keeps the checkpoint | AGT-O-11 | 1 |
| Rate limits | Per principal at the gateway | `limit.rate` | AGT-O-11 | 0 |
| Errors | RFC 9457 shape, typed context, ordered fixes | Third-party fixes labelled and restricted | AGT-O-1 | 0 |
| SDKs | Generated from one schema | Schema drift fails the build | AGT-O-2 | 1 (Rust, Python), 2 (TypeScript) |

## Method catalog

Every method is `<group>.<name>` in the eight groups of contract section 7.6. ECO's registry, event, archive and capability methods and KLN's lifecycle methods join these groups, and release, yank, export and deviation grants are Act classes. A breaking change creates a new version such as `edit.apply@2`, and the old one is served for at least twelve months [S2].

Methods marked † change state or spend budget, so they need an idempotency key and, except `session.open`, a session. Read and Inspect methods accept a `ChangeRef` (a Change, `branch@head` or a tag), and every result carries its labels. Approvals are not methods: assigned humans give them on the server's approval page (D-AGT-20).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `session.open` † | `SessionOpen` → `SessionOpened` | `auth.scope_denied`, `session.branch_protected`, `label.exceeds_clearance` | AGT-O-7 | 0 |
| `session.status` | Handle → head, grant, context label, usage, open Evaluations | `session.expired` | AGT-O-1 | 0 |
| `session.close` † | Handle → final usage; unused budget returned | `session.unknown` | AGT-O-11 | 0 |
| `session.control` † | Pause, resume or steer a hosted-crew session; delegating human only | `auth.not_delegator` | AGT-O-7 | 2 |
| `session.presence` † | Share selection or camera with an agent session; delegating human only | `auth.not_delegator` | AGT-O-7 | 2 |
| `read.tree` | Path → entries with kind, size, hash and labels | `read.not_found` | AGT-O-1 | 0 |
| `read.source` | Path, range → text with free-text spans as handles (D-AGT-18) | `read.not_found`, `label.exceeds_clearance` | AGT-O-8 | 0 |
| `read.outline` | Path or feature → calls, parameters, checks, spans | `build.parse_failed` (partial outline) | AGT-O-1 | 0 |
| `read.history` | Branch → Changes with provenance; messages as handles | `read.not_found` | AGT-O-10 | 0 |
| `read.branches` | Repository → name, head, protection, owner | — | AGT-O-1 | 0 |
| `read.symbols` | Query → path, kind, signature, doc URI | — | AGT-O-16 | 1 |
| `read.docs` | Symbol, error code or URI → `DocEntry`s pinned to the lockfile | `docs.not_found` with nearest matches | AGT-O-16 | 0 (errors), 1 (std) |
| `read.external_text` | Handle → typed extract, or raw text where D-AGT-25 allows | `label.raw_external_forbidden` | AGT-O-8 | 0 (handles), 2 (extracts) |
| `read.value` | `ValueRef` → typed value; marks the context `data_untrusted` | `read.unknown_handle` | AGT-O-17 | 1 |
| `read.bom`, `read.where_used` | KLN's EBOM, then MBOM, service BOM and where-used | `read.not_found` | AGT-O-1 | 1 (EBOM), 2 |
| `read.catalog` | Filters → catalog part summaries | `catalog.filter_invalid` | AGT-O-1 | 2 |
| `read.packages`, `read.package`, `read.registry_bundle` | ECO registry search, package metadata and signed offline bundles | `package.not_found` with nearest names; `package.unavailable` (bundles) | AGT-O-1 | 1 (`read.package`), 2 |
| `read.events` | Source, cursor → events in sequence order | `events.cursor_expired` | AGT-O-1 | 1 |
| `read.subscribe`, `read.unsubscribe` | Create or delete a webhook subscription; people with `maintainer` or `admin` only; thin payloads (ECO) | `events.url_refused` | AGT-O-22 | 1 |
| `read.machine_data` | Machine → state and as-run records from MFG's gateway | `mfg.gateway_unreachable` | AGT-O-1 | 2 |
| `read.audit` | Filter → audit entries; needs `audit:read` | `auth.scope_denied` | AGT-O-20 | 1 |
| `inspect.scene` | Root, depth, include → `SceneGraph` | `build.failed` (partial graph), `inspect.too_large` (cursor) | AGT-O-3 | 1 |
| `inspect.entity` | Entity → kind, surface type, size, adjacency, provenance chain | `inspect.entity_gone` with `HistoryRecord`s | AGT-O-3 | 1 |
| `inspect.query` | Ingot query → entities with resolution notes | `query.resolve_failed` with candidates | AGT-O-18 | 1 |
| `inspect.suggest_query` | Entities → robust queries with stability scores | `query.no_robust_candidate` | AGT-O-18 | 1 |
| `inspect.measure` | Distance, angle, clearance, wall thickness, mass, interference → `Quantity`, `ErrorBound`, witnesses | `inspect.kind_unsupported` | AGT-O-3 | 1 |
| `inspect.render` | `RenderRequest` → `Rendered` snapshot | `render.too_many_marks` | AGT-O-3 | 1 |
| `inspect.ask_render` | Template, marks → mark ids, booleans or counts | `render.template_unknown` | AGT-O-8 | 2 |
| `inspect.section` | Plane → curves, SVG, legend | `inspect.empty_section` with the nearest offset | AGT-O-3 | 1 |
| `inspect.field` | Points, region, statistics or extrema → values with error and validity zones | `field.out_of_domain` | AGT-O-3 | 1 |
| `inspect.describe` | Target, detail → `Description` | `build.failed` (describes what built) | AGT-O-4 | 0 |
| `edit.apply` † | `ApplyEdits` → `EditsApplied` | `edit.*`, `label.write_down` | AGT-O-6 | 0 |
| `edit.revert` † | Changes → a forward Change | `edit.revert_conflict` | AGT-O-6 | 0 |
| `edit.undo` † | One repository transaction from KLN's log; own branches only | `edit.not_owner` | AGT-O-6 | 0 |
| `edit.create_branch`, `edit.reset_branch` † | Create a branch owned by the session's principal; reset an own unprotected branch | `edit.branch_exists`, `edit.branch_protected` | AGT-O-6 | 0 |
| `edit.import_archive` † | ECO repository archive → a new design repository | `archive.incomplete` listing missing objects | AGT-O-1 | 1 |
| `edit.grant_capability`, `edit.revoke_capability` † | A scoped Wasm component capability grant or revocation in `ingot.lock` (ECO) | `policy.denied` naming the rule | AGT-O-7 | 1 |
| `evaluate.build` † | Targets, `Fidelity`, `estimate_only` → `BuildReport` | `budget.exceeded`, `build.failed` | AGT-O-11 | 0 |
| `evaluate.checks` † | Selection, `Fidelity` → `CheckOutcome`s | As above | AGT-O-1 | 0 |
| `evaluate.simulate` † | Study, `Fidelity` → Fields with `ErrorBudget`s and validity zones | `flux.study_invalid`; zones flag, never hide | AGT-O-1 | 1 |
| `evaluate.manufacture` † | Setup → toolpaths, collisions, removal simulation, cycle time | `mfg.setup_invalid` | AGT-O-1 | 2 |
| `evaluate.cost` † | Quantity, process → cost lines with intervals and price sources | `cost.unpriced_lines` (partial report) | AGT-O-1 | 1 |
| `evaluate.ci` † | Change → the `CiReport` that Proposal CI would produce | — | AGT-O-14 | 1 |
| `evaluate.explore`, `evaluate.materialize` † | Exploration → Pareto frames; a variant → `SetParameter` edits | `explore.no_feasible_point`, `explore.variant_unknown` | AGT-O-13 | 2 |
| `evaluate.get` | Evaluation, `after_frame`, `wait_ms` ≤ 25,000 → status, frames, result | `evaluation.unknown` | AGT-O-1 | 0 |
| `evaluate.cancel` † | Evaluation → status; cancellation is an Abort | — | AGT-O-1 | 0 |
| `compare.diff` | From, to, levels → `SemanticDiff` with an optional overlay snapshot | `compare.unrelated` (computed and flagged) | AGT-O-14 | 1 |
| `compare.merge_preview` | Base, left, right → KLN's conflicts and merged result, nothing written | — | AGT-O-6 | 1 |
| `compare.resolve` | Manifest, lockfile → a new lockfile and its diff, not applied (ECO) | `package.unsatisfiable` with the explanation | AGT-O-1 | 1 |
| `propose.create`, `propose.update` † | Title, rationale, target, parent, draft, ready → `Proposal` | `propose.preconditions_failed`, `propose.closed` | AGT-O-14 | 1 |
| `propose.get`, `propose.list` | Proposals, with free text as handles | — | AGT-O-8 | 1 |
| `propose.review` † | Verdict, findings → `Review` | `propose.self_review_forbidden` | AGT-O-7 | 1 |
| `propose.comment` † | Anchor, body → `Comment`; an @mention of an agent becomes an inbox request | — | AGT-O-7 | 1 |
| `propose.merge`, `propose.withdraw` † | Expected head → merged Change; or a reason | `propose.policy_unsatisfied`, `propose.conflict` | AGT-O-14 | 1 |
| `propose.endorse_text` † | Spans → endorsed by a human who sees them verbatim, hidden characters highlighted | `auth.human_only` | AGT-O-8 | 1 |
| `propose.policy` † | A Proposal to policy files; humans merge, two of them for D-AGT-27 changes | `label.untrusted_context`, `auth.human_only` | AGT-O-7 | 1 |
| `propose.declassify` † | A declassification record for two signers, one an export officer; KLN stores it | `auth.human_only` | AGT-O-17 | 1 |
| `propose.plan` † | Plan → validated plan and work-item states | `plan.invalid` | AGT-O-12 | 2 |
| `propose.change_request`, `propose.change_order` † | KLN lifecycle records; a change order's approvals are those of its release plan | `propose.preconditions_failed` | AGT-O-9 | 2 |
| `propose.purge` † | KLN purge request for two administrators | `auth.human_only` | AGT-O-7 | 2 |
| `act.prepare` † | Class, payload → `ActionPlan` with digest | `act.recipient_unverified`, `label.exceeds_clearance` | AGT-O-9 | 1 |
| `act.commit` † | Plan digest → `act.approval_pending { request }` until approved, then `ActionReceipt` | `act.plan_changed`, `act.denied`, `act.onsite_required` | AGT-O-9 | 1 |
| `act.status` | Plan digest → state, approvals, receipt | — | AGT-O-9 | 1 |

## Observation interfaces

Agents perceive designs through a scene graph, exact geometry queries, snapshots with marks and Field overlays, template-generated descriptions and semantic diffs. Every channel answers from the same Kiln results, every geometric value carries its `ErrorBound`, and a text-only model receives the same facts as a vision model.

### Structured scene graph

`inspect.scene` returns the evaluated product as a typed tree, computed from Kiln results for one Change and never from UI state.

Each `SceneNode` carries its instance path (`gearbox/input_shaft[1]`), kind, item identity, producing feature and source span, placement, material, representation, bounding box and mass properties with `ErrorBound`s, verdict counts with the worst margin, available Fields and children. The default response is depth 2 with identical sibling Instances collapsed into one node with a count. A failed build returns the partial graph with a diagnostic on each failed node.

### Geometry queries

- `inspect.query` evaluates an Ingot query such as `part.faces(normal: +z, area > 100mm2)` and returns entities with their `Merged`, `FragileAnchor` or `RankSwap` notes, or a typed `ResolveError` with candidates.
- `inspect.entity` returns an entity's surface or curve type, size, adjacency and provenance from `HistoryRecord`s.
- `inspect.measure` returns a `Quantity` with an `ErrorBound` and witness points, such as the thinnest location for wall thickness.
- `inspect.suggest_query` takes entities an agent picked from a snapshot and returns queries that keep resolving to them.

**Decision D-AGT-8:** Agents select geometry only through `Query` expressions and `EntityId`s. `inspect.suggest_query` ranks candidates by how stably they resolve over the full declared range of every parameter, endpoints included, plus ±10% around current values, and reports `Note::RankSwap { at }` where the winner's lineage changes. *Why:* rank selectors flip silently inside declared ranges, which sampling near current values misses: the canonical bracket's `width` spans 20 mm to 400 mm (R2-22). *Rejected:* indices or screen coordinates in source; trusting the first query that resolves; ±10% sampling alone. (revised in round 2)

A suggested query reports its stability score, the fraction of perturbed rebuilds that resolve to the corresponding entities. Agents submit queries scoring 1.0 unless the Proposal rationale states a deviation. Rank selectors appear only after a provenance anchor or role filter, as contract section 5 requires.

### Snapshots and Field overlays

```rust
pub struct RenderRequest {
    pub change: ChangeRef,
    pub targets: Option<Vec<InstancePath>>,
    pub views: Views,                    // Named(Iso | Front | Top | Right) | Grid4 | Custom(Camera)
    pub style: Style,                    // Shaded | HiddenLine | Wire | XRay
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
    pub untrusted: bool,                 // D-AGT-26
    pub visible_summary: String,
}
```

Marks follow Set-of-Mark prompting, which let GPT-4V beat a fine-tuned referring-expression model zero-shot on RefCOCOg [S36]. Each label maps to an `EntityId`, so "fillet the edges marked 3 and 7" resolves exactly. `Grid4` returns four views in one image, as Zookeeper's self-review uses [S11].

**Decision D-AGT-9:** Agent snapshots come from UIX's headless renderer with a `RenderProfile` in the request and the snapshot key, and return marks, legend and extrema as data plus a plain-text summary. Snapshots are non-canonical: they carry `PlatformClass::Unverified` and the renderer identity, never enter an `OpKey` or an approval subject, and are compared by ꟻLIP thresholds [S62]; byte identity holds only on one pinned CI renderer image. *Why:* software rasterizers generate code at run time for the host CPU [S61], so byte identity across the canonical class cannot hold (R6-26), and locale, theme and units change legends (R3-35). *Rejected:* calling CPU renders canonical; images without structured side data (vision models misread small labels and colours). (revised in round 2)

Proposals and benchmarks use the review profile: `en`, SI with millimetres, light theme. Snapshots attached to a Proposal are stored once as Assets, so reviewers, verifiers and approvers see the same bytes.

**Decision D-AGT-26:** A snapshot is untrusted and instruction-capable when the geometry or appearance of any visible Body derives from an untrusted Asset. Agent snapshots default to `appearance: Neutral`, which drops imported textures. A context that must stay free of `instruction_tainted` asks about an untrusted snapshot only through `inspect.ask_render`, a quarantined vision call with a fixed template whose answers are mark ids, booleans or counts. *Why:* embossed letters and texture maps can carry instructions, yet tainting every snapshot of an assembly with one supplier part would make vision useless (R5-17). *Rejected:* treating every snapshot as trusted; tainting every snapshot that contains a supplier part.

The scene graph, measurements and descriptions stay non-tainting, because they carry typed values and handles only.

### Sections and descriptions

`inspect.section` cuts the design with a plane and returns section curves with the cut-plane `ErrorBound`, an SVG hatched per material and an optional overlay. An empty cut returns the nearest offset that intersects material.

`inspect.describe` produces a description of a design, feature, Instance or diff from typed facts by templates, without any model. Its result has `text` (Markdown), `facts` (every number with source and bound) and `detail` (`Brief` up to 80 words, `Standard` up to 400, `Full`). The canonical bracket of contract section 6 at the brief level:

> Part `bracket` (item 100-0042), aluminium 6061-T6. Bounding box 60.0 × 40.0 × 24.0 mm; mass 39.2 g ± 0.1 g. Features: sketch, extrude 4 mm, rib 20 mm, fillet 2 mm on 2 edges. Checks: 1 of 1 `Pass` at `Interactive`: regularized peak von Mises stress away from the clamp 112 MPa ± 9 MPa (`Estimated`) against 165.6 MPa, margin 27% at the bound.

**Decision D-AGT-10:** Canonical descriptions are generated from typed facts by templates and contain no model text; models may summarize them, but the canonical form is the one stored, diffed and shown in review. Phrasing from std and `crucible::` templates is trusted; any third-party template, from a verified publisher or not, renders as typed facts plus an `ExternalText` handle for its phrasing. *Why:* descriptions feed reviews and benchmarks, so every number must trace to a fact, and publisher verification establishes identity, not safe text (R5-13). *Rejected:* model-written canonical descriptions; trusting verified publishers' templates. (revised in round 2)

### Semantic diffs

`compare.diff` explains what changed between two Changes:

| Level | Content |
| --- | --- |
| Source | Formatted Ingot text diff, free text as handles |
| Features | Features added, removed, moved; parameters old → new with units |
| Checks | Verdict and margin changes; checks added, removed or loosened |
| Geometry | Volume added and removed, Hausdorff deviation with `ErrorBound` (Anvil) |
| Metrics | Mass, cost, regularized peaks, cycle time and declared objectives, with intervals |
| BOM | Lines added or removed, quantity changes, new catalog parts |
| Policy | Checks, tolerances, oracle references, protected paths, lockfile pins, recipient records |

The overlay snapshot shows added and removed material in a colour-blind-safe pair, with unchanged geometry ghosted. Any diff at the policy level sets `policy_sensitive: true`, which risk classification reads.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Scene graph and measurements | Typed tree from Kiln results; `Quantity` with `ErrorBound` and witnesses | Partial graph with diagnostics | AGT-O-3 | 1 |
| Geometry queries | `Query` and `EntityId` only; notes surfaced | `query.resolve_failed` with ranked candidates | AGT-O-18 | 1 |
| Query robustness ranking | Full declared range plus ±10%; `RankSwap` reported | `query.no_robust_candidate` | AGT-O-18 | 1 |
| Snapshots and overlays | `RenderProfile` in the key; `Unverified` class; ꟻLIP comparison; legends as data | `render.too_many_marks` | AGT-O-3 | 1 |
| Untrusted snapshots | Neutral appearance; quarantined `inspect.ask_render` | Reading one directly sets `instruction_tainted` | AGT-O-8 | 2 |
| Sections | Curves with bounds, SVG, overlay | `inspect.empty_section` with nearest offset | AGT-O-3 | 1 |
| Descriptions | Template-generated; every number a fact; third-party phrasing as handles | Describes what built | AGT-O-4 | 0 (source facts), 1 (evaluated facts) |
| Semantic diffs | Seven levels; `policy_sensitive` flag | `compare.unrelated` flagged | AGT-O-14 | 1 |

## Roles

A role is a `Role` record published as a package: name and version, scopes, a write-set rule (none, from the work item, or fixed globs), an external-text policy (never, or extracts), exit checks, outputs, model requirements and a skill at `skill://crucible/<role>/SKILL.md` with its manifest digest. The crew is the set of roles in the open-source `std::agents` package, and anyone can publish a role the same way.

**Decision D-AGT-11:** Roles are data plus instructions in an open package, and their exit criteria are checks in `std::agents::exit`, evaluated by CI over the Proposal through a typed `std::agents::proposal` view. *Why:* "no privileged code" applies to agents too, and exit criteria must be machine-checkable to be oracles. *Rejected:* roles hard-coded in the runtime (privileged and opaque); prose-only exit criteria (not enforceable). (revised in round 2)

A role skill changes only through a reviewed Proposal to `std::agents`, gated by the agent benchmarks. The hosted crew loads a role from another publisher only after `policy:admin` approves that version and manifest digest.

### Scopes

Scopes are the units of permission in grants, tokens and roles. There is no wildcard scope, and hosts request scopes incrementally by step-up [S7].

| Scope | Grants |
| --- | --- |
| `design:read` | Read, Inspect and Compare methods, except `read.external_text`, `read.value` and `read.audit` |
| `external:read` | `read.external_text` and `read.value`, under D-AGT-25 |
| `design:edit` | Edit methods on the session's branch, within its write set |
| `eval:build`, `eval:simulate[:fidelity]`, `eval:manufacture`, `eval:cost`, `eval:explore` | The matching Evaluate methods, simulation up to the stated fidelity |
| `propose:author`, `propose:review`, `propose:merge`, `propose:plan` | Authoring; review except of the reviewer's own lineage; merge when policy is satisfied; plans and child sessions |
| `act:<class>` | `act.prepare` and `act.commit` for one Act class; commit always waits for an assigned human |
| `audit:read` | `read.audit` |
| `policy:admin` | Policy, protection, clearances, recipients and auto-merge; humans only, never obtainable by token exchange |

### Role catalog

Every role holds `design:read` and `propose:author`. The verifier and the DFM reviewer also hold `propose:review`; the planner holds `propose:plan` and `propose:merge` limited to its integration branch.

| Role | Writes | External text | Exit checks (`std::agents::exit`) | Acts it may prepare | Phase |
| --- | --- | --- | --- | --- | --- |
| Planner | Its integration branch, only by merging children | Never | `plan_is_acyclic`, `parallel_write_sets_disjoint`, `every_item_has_acceptance_checks`, `budgets_within_parent`, `parent_ci_green`, `verifier_approved` | None | 2 |
| Requirements analyst | `requirements/**` | Extracts | `every_requirement_has_id_and_source`, `every_requirement_has_verification_method`, `quantities_typed`, `open_questions_listed` | None | 2 |
| Concept designer | Own concept branches | Never | `concepts_distinct`, `each_concept_builds`, `requirements_coverage_reported` | None | 2 |
| Detail designer | Work-item write set | Never | `builds_at_declared_fidelity`, `all_checks_pass`, `no_new_fragile_queries`, `tolerances_on_mating_features`, `no_allow_errors_changes` | None | 1 |
| Simulation engineer | `studies/**` and checks on results | Never | `convergence_demonstrated`, `results_within_validity_envelope`, `loads_trace_to_requirements`, `signoff_fidelity_for_release_checks`, `verification_case_passed` | None | 1 |
| DFM reviewer | None; findings carry fixes | Never | `every_finding_anchored`, `every_blocker_has_fix_or_rationale`, `rules_version_recorded` | None | 2 |
| CAM programmer | `mfg/cam/**` | Extracts (tool data) | `no_collisions`, `no_gouges`, `stock_removed_within_tolerance`, `tools_in_library`, `feeds_within_tool_limits`, `posted_for_named_machine` | `send_to_machine`, `store_machine_job` | 2 |
| Cost engineer | `cost/**` and cost-reduction branches | Extracts (quotes) | `every_bom_line_priced_or_flagged`, `prices_have_source_and_date`, `totals_have_intervals` | `request_quote` | 2 |
| Drawing and MBD author | Drawing source and PMI | Never | `every_feature_of_size_toleranced`, `datum_reference_frames_complete`, `annotations_reference_live_entities`, `pmi_semantic_in_ap242_export` | None | 2 |
| Catalog librarian | Catalog package repository | Extracts | `key_dimensions_match_datasheet`, `units_typed`, `geometry_licence_recorded`, `provenance_recorded` | `publish_package` | 2 |
| Documentation writer | `docs/**` except drawings | Never | `every_number_cites_a_fact`, `facts_current_at_head`, `snapshots_within_threshold` | None | 2 |
| Independent verifier | Own scratch and counter-proposal branches | Never | `attack_catalog_covered`, `findings_reproducible`, `mutation_score_reported` | None | 1 |

Phase 1 ships the three roles contract section 13.2 names, run from external MCP hosts; the CAM programmer arrives with CAM in phase 2, and MFG's agent-proposed toolpaths with it (R4-12). Ambiguous inputs become open questions, and a value a role cannot source, such as a tolerance or a price, becomes a finding for a human, never an invention.

Reviewers never edit what they review, and catalog librarian Proposals always carry `data_untrusted`. A CAM program is offered to a human programmer step by step, as CloudNC's CAM Assist offers strategies for acceptance [S15].

### Planner

The planner turns a goal into a validated plan, dispatches work items and assembles the parent Proposal; it never edits design source. It reads requirements and the design, never external text, so its actions are fixed before untrusted data is processed (Plan-Then-Execute [S25]). After an item exhausts its attempts, it re-plans once, then escalates to the delegating human with the typed failure history.

### Independent verifier

The verifier runs with a fresh context that shares no session lineage with the author, and with a different model family where policy requires. In phase 1 it runs in any MCP host under its own principal, and the server checks the lineage. It reasons over a typed view: typed requirements, the IR, the semantic diff, check outcomes, the CI report and the rationale's structured fields, with the author's free text elided.

Every review tries at least uncovered requirements, worst-case tolerance stacks, load cases the studies omit, material extremes, check mutation, query fragility, CI replay in another platform class and manufacturability. Check mutation thins walls by 50%, removes fillets, doubles loads and swaps in the weakest permitted material; a check that passes under every mutation is reported as possibly vacuous. Findings come with an Ingot test that fails on the Proposal head.

**Decision D-AGT-12:** Every agent Proposal is attacked by an independent verifier that shares no lineage with the author, reasons over a typed view with the author's free text elided, and runs a fixed attack catalog that includes check mutation. *Why:* self-review shares the author's blind spots, mutation testing turns "the checks pass" into evidence that they can fail, and author text addressed to the verifier is an injection channel (R5-02). *Rejected:* self-verification only (Zookeeper-style snapshot review [S12] is useful but not independent); render-question verification only (CADCodeVerify reports a 7.30% reduction in point-cloud distance [S17], but it cannot detect a check that cannot fail); a verifier that reads the rationale's prose with a taint label. (revised in round 2)

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Role packages | `Role` records with skills and manifest digests in `std::agents` | Unapproved manifest refuses the role in the hosted crew | AGT-O-1 | 1 |
| Scopes | No wildcard; incremental step-up; `policy:admin` human-only | `auth.scope_denied` | AGT-O-7 | 0 |
| Exit checks | `std::agents::exit` over the typed Proposal view | `propose.preconditions_failed` | AGT-O-15 | 1 |
| Phase 1 roles | Detail designer, simulation engineer, verifier | `session.role_unavailable` | AGT-O-15 | 1 |
| Further roles | The nine others in the catalog | `session.role_unavailable` | AGT-O-15 | 2 |
| Independent verifier | Lineage-independent; typed view; attack catalog; mutation | Merge blocked until a verifier review exists at head | AGT-O-19 | 1 |

## Orchestration of swarms

A swarm is a tree of Proposals. A planner writes a plan, workers deliver child Proposals on their own branches, a merge queue integrates them, and a verifier attacks the result before it reaches the target.

### When to use a swarm

Anthropic reports that multi-agent systems use about 15× the tokens of chat and suit heavily parallel work, while coding tasks parallelize less well [S33]. Design work is closer to coding: most edits touch one feature tree.

**Decision D-AGT-13:** The default is a single agent; the runtime starts a swarm only when a validated plan has at least two work items that can run in parallel. Caps by default: 8 parallel workers per Proposal tree and a delegation depth of 2 (planner, then workers that cannot spawn agents). *Why:* cost grows faster than benefit when work is not parallel; Anthropic saw failure modes such as spawning 50 subagents for simple queries [S33]. *Rejected:* always-on swarms (cost, merge churn); unbounded recursive delegation (cost and accountability blur).

### Plans and work items

```rust
pub struct WorkItem {
    pub id: WorkItemId,
    pub role: RoleRef,
    pub requirements: Vec<RequirementId>,
    pub write_set: WriteSet,
    pub depends_on: Vec<WorkItemId>,
    pub acceptance: Vec<CheckRef>,       // must exist, or be added by the item, and pass
    pub budget: Budget,
    pub max_attempts: u8,                // default 3
    pub state: WorkItemState,            // Pending | Leased { session, attempt, until } | Proposed | Merged | Failed
}
```

A `Plan` holds the goal, the items, the integration branch, a budget carved from the parent Proposal and `max_parallel` (default 8). `propose.plan` checks that the graph is acyclic, that items able to run concurrently have disjoint write sets, that every item names acceptance checks, that budgets fit and that every role has a qualified endpoint; failures return `plan.invalid` with fixes. A valid plan makes the server create the integration branch, owned by the planner's session.

### Execution

[[DIAGRAM diagrams/09-agents-swarm-flow.jsx: swarm flow · planner, parallel workers, merge queue, two verifiers]]

1. **Dispatch.** The runtime leases each ready item up to `max_parallel`, opening a child session on a branch forked from the integration head with the item's write set, scopes and budget.
2. **Work.** The worker reads, edits, builds, checks and inspects, then proposes into the integration branch.
3. **Light verification.** A verifier checks each child for uncovered requirements, check mutation and query fragility.
4. **Merge queue.** Children merge in dependency order with CI on each merged result, so the integration head always passes every `Error`-severity check.
5. **Assembly and review.** The planner points the parent Proposal at the target, the verifier runs the full catalog, and the Proposal flow follows.

A lease lasts 10 minutes and any call renews it. An expired lease returns the item to `Pending` with an incremented attempt, and writes from a stale attempt fail with `session.lease_lost`. Plan state lives on the parent Proposal, so the crew resumes from the repository after a restart.

### Coordination without messages

**Decision D-AGT-14:** Agents never message each other directly. Plans, work items, Proposals, reviews and anchored comments are the only coordination medium, each written through the API by an authenticated principal. *Why:* every coordination act is versioned, auditable and visible to humans; spoofed agent messages are a named risk (ASI07 [S30]); any MCP host can join a swarm without a second protocol. *Rejected:* direct messaging, including A2A 1.0 [S51] (a second protocol outside the design history); a shared scratch memory (unreviewed and poisonable, ASI06 [S30]).

A comment from another agent reaches the reader as an `ExternalText` handle, so agents exchange facts through typed objects: failure reports, findings with reproducing tests and check outcomes.

### Conflict resolution

| Stage | Outcome |
| --- | --- |
| Prevention | Concurrent items have disjoint write sets; overlapping ones run in sequence |
| Semantic conflict | A conflict on a feature, parameter, entity or net returns the item to its worker as typed input |
| Behavioural conflict | Children pass alone but the merge fails a check: a reconcile item gets both diffs and the failing check |
| Alternatives | Competing passing solutions are ranked by the plan's objectives; a tie goes to a human |
| Exhaustion | One re-plan, then the delegating human sees both alternatives with failure histories |

### Design-space exploration

`evaluate.explore` searches a parametric space for trade-offs, evaluating variants in parallel through Kiln and Flux. Variants are parameter assignments in an exploration record in CAS, not branches. A request names variables, objectives with units, constraints (default: every `Error`-severity check), a fidelity ladder, a strategy, a batch size, a budget and a seed.

| Situation | Strategy |
| --- | --- |
| Initial design | Scrambled Sobol sequence of 2(d + 1) points |
| Expensive variants (under about 500 affordable, up to about 50 variables) | Bayesian optimization: qLogNEHVI, or qLogNoisyExpectedImprovement for one objective [S37][S38]; dimension-scaled lengthscale priors [S40] |
| Cheap variants or mostly categorical spaces | NSGA-II for two objectives, NSGA-III for more [S41] |
| Several fidelities or separable objectives (phase 3) | Hypervolume knowledge gradient [S39] |

**Decision D-AGT-15:** Exploration strategies are implemented in Rust and published as the Wasm component package `std::explore`, with BoTorch and pymoo as reference implementations rather than embedded dependencies. *Why:* the contract puts heavy custom algorithms in Wasm components, and Python and PyTorch cannot run deterministically in the sandbox, on every OS or in the browser. *Rejected:* a Python sidecar running BoTorch (no browser, no determinism, a second runtime); evolutionary methods only (they need many more variants when each costs a Flux solve [unverified as a general figure]).

- **Failures** are recorded with their typed errors, and a Gaussian-process classifier weights the acquisition by build success.
- **Validity.** Results in `Invalid` or `Extrapolated` zones leave the Pareto front by default.
- **Fidelity ladder.** Screening runs at `Interactive` and the top five points rerun at `SignOff`; a point whose enclosures do not overlap is flagged `fidelity_disagreement`.
- **Determinism.** Seeds are inputs, Gaussian processes fit by deterministic L-BFGS from fixed Sobol restarts, and synchronous rounds are the default.

### Scheduling on Kiln workers

Kiln owns Op scheduling; this tab owns admission and accounting. Every Evaluation carries a `PriorityClass`:

| Class | Used by | Preemption |
| --- | --- | --- |
| `Interactive` | Sessions where a human is waiting | Never preempted |
| `Agent` | Agent sessions | By `Interactive`, at Op boundaries |
| `Ci` | Proposal CI and merge queues | By `Interactive` |
| `Batch` | Explorations and benchmarks | By all; resumes from cached Ops |

Within a class, Kiln shares capacity among principals by dominant resource [unverified: Dominant Resource Fairness named from general knowledge]. The planner and verifier may use the strongest qualified endpoint and workers a cheaper one. Anthropic's Opus 4 lead with Sonnet 4 subagents beat a single Opus 4 agent by 90.2% on an internal benchmark [S33], a hypothesis Crucible measures on golden tasks.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Plans and validation | Acyclic, disjoint concurrent write sets, acceptance checks, budgets | `plan.invalid` with fixes | AGT-O-12 | 2 |
| Leases and fencing | 10-minute leases; attempt numbers fence stale writers | `session.lease_lost` | AGT-O-12 | 2 |
| Merge queue | Children merge in dependency order with CI per merge | Conflicts return to the worker as typed input | AGT-O-12 | 2 |
| Exploration | `std::explore`: Sobol, NSGA-II and III, Bayesian optimization; deterministic in synchronous mode | `explore.no_feasible_point`; failures counted | AGT-O-13 | 2 |
| Multi-fidelity exploration | Hypervolume knowledge gradient | Falls back to single-fidelity search, reported | AGT-O-13 | 3 |
| Priority classes | Four classes with preemption at Op boundaries | — | AGT-O-11 | 0 |

## Proposals and review

A Proposal is a branch plus rationale plus CI report, stored by `repo`.

### The Proposal object

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
    pub snapshots: Vec<AssetId>,         // server-generated at head, review profile
    pub risk: RiskAssessment,            // class and the diff items that set it
    pub labels: Labels,                  // join of every authoring context's label
    pub reviews: Vec<Review>,
    pub state: ProposalState,            // Draft | Open { ready } | Merged | Withdrawn | Superseded
    pub usage: Usage,
}
```

`Rationale` holds a summary, requirement ids, design choices with evidence ids, deviations and known limitations. Before `propose.create` without `draft`, the server checks:

1. The head builds at each target's declared fidelity.
2. Every `Error`-severity check has the verdict `Pass` at its declared fidelity; a conditional pass counts only under a covering policy allowance (contract sections 5 and 7.6). Waiving a check in source is a loosening, hence R3.
3. Snapshots exist at the head: a `Grid4` of each changed Part or Assembly, a geometry-overlay diff and an overlay for each changed study result.
4. The rationale has a summary and, where the repository declares requirements, at least one requirement link.
5. Every Change on the branch carries complete provenance.

A failure returns `propose.preconditions_failed` with the failing items and fixes. Drafts skip items 1 to 3 and cannot be reviewed for merge or merged.

### CI report

`service:ci` produces the `CiReport` on untrusted-evaluation workers (contract section 7.8). No agent can write or edit it, and `evaluate.ci` gives agents the identical report in advance. After merge, trusted builders recompute what releases and `SignOff` gates need.

A `CiReport` names the Change and lockfile digest and holds build and check outcomes per platform class, cross-class agreement, every `CheckOutcome`, margin and metric deltas against the target's head, validity-zone flags, oracle integrity (protected paths untouched or approved) and usage.

### Risk classification

The server classifies every Proposal from its semantic diff and the labels of its authoring contexts.

| Class | Meaning | Examples |
| --- | --- | --- |
| R0 | No semantic change | Formatting and comments with an identical IR hash; regenerated snapshots |
| R1 | Contained design change | Parameter changes within declared ranges on unreleased designs; no check, tolerance, BOM or dependency change; no margin below 90% of its target-head value; every authoring context clean |
| R2 | Ordinary design change | New features, checks, studies or materials; BOM changes; dependency updates that keep behavior versions; any R1-shaped change from a `data_untrusted` context |
| R3 | Sensitive change | Checks or tolerances loosened or waived; oracle references; protected paths; behavior-version bumps; change orders; any change from an `instruction_tainted` context |
| R4 | Critical | Changes feeding an Act class (a release candidate, a posted program, files bound for a supplier); policy files; recipient records |

**Decision D-AGT-16:** Risk class is a deterministic function of the semantic diff, the target and the integrity flags of every authoring context. Loosening any check or tolerance, or any content from an `instruction_tainted` context, is at least R3; any content from a `data_untrusted` context is at least R2. *Why:* loosening a check to make it pass is the cheapest reward hack, and untrusted typed values can steer edits without carrying text (R5-01). *Rejected:* model-assessed risk (manipulable, non-reproducible); one class for all agent work (review fatigue, ASI09 [S30]). (revised in round 2)

### Human review and separation of duties

UIX's review view adds, for agent Proposals, the provenance panel, the risk class and its reasons, integrity flags with their sources, the verifier report and the canonical description. Findings anchor to `EntityId`s, feature paths or source spans and return to the author as typed input.

- No principal in the delegation chain may approve the Proposal, except the delegating human for R0 to R2.
- R3 and R4 need a human outside the chain; repository policy can require more.
- Agent reviews never count toward human approval requirements.
- Phones never approve or merge (contract section 9).

### Auto-merge

Auto-merge is a repository policy, off by default, changed only by two humans (D-AGT-27).

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

**Decision D-AGT-17:** Auto-merge applies only to R0 and R1 Proposals whose authoring contexts were all free of `instruction_tainted` and `data_untrusted`, approved by a verifier from a clean context, CI-green in two platform classes and unvetoed through a quiet period. R2 and above always need a human. *Why:* low-risk changes should not queue behind people, but anything that can change behavior meaningfully needs accountability (R5-01). *Rejected:* auto-merge on "all checks pass" alone (checks can be incomplete); no auto-merge ever (review fatigue degrades attention where it matters). (revised in round 2)

`service:merge` performs auto-merges after the quiet period, never the authoring agent, and provenance records the policy version. An organization-wide agent freeze stops auto-merge, new agent sessions and all agent writes within 5 seconds (target).

### Provenance of agent changes

The API server writes and signs a record for every Change, so an agent cannot forge its own.

```rust
pub struct ChangeProvenance {
    pub change: ChangeId,
    pub principal: PrincipalId,
    pub delegation: Vec<PrincipalId>,
    pub session: SessionId,
    pub role: Option<(RoleRef, Sha256)>,         // role version and skill manifest digest
    pub endpoint: Option<EndpointRecord>,        // D-AGT-21
    pub assurance: Assurance,                    // Attested (crew or gateway) | Declared
    pub instructions: Sha256,                    // goal, work item, skill, system prompt
    pub client: ClientInfo,
    pub context: Labels,
    pub inputs: Vec<ReadRecord>,                 // digests of what the context read
    pub transcript: Option<ObjectId>,            // hosted crew always; other hosts if uploaded
}
```

Each record is an in-toto Statement v1 with the Change digest as `subject` and a Crucible `predicateType` [S48], signed by the deployment's provenance key. Crucible attests the model only when its crew or model gateway made the call; otherwise the identity is `Declared` and review says so. Instructions and transcripts are stored under the context's label and their own retention (D-AGT-32).

### Reversibility

| Effect | Undone by |
| --- | --- |
| Change on an agent's own branch | `edit.reset_branch`, `edit.undo` or `edit.revert` |
| Merge, swarm result or auto-merge | `edit.revert` of the merge as a forward Change in a Proposal; a daily digest lists auto-merges with revert links |
| Release | Not undoable; superseded by a change order and a new release |
| Compensable or revocable Act | Cancellation or revocation, recorded as a new Act |
| Irreversible Act | Not undoable, hence approval of the exact plan |

History on protected branches is never rewritten.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Proposal records | Fields above; labels joined from authoring contexts | `propose.closed` | AGT-O-14 | 1 |
| Preconditions | Build, `Error`-severity checks `Pass`, snapshots, rationale, provenance | `propose.preconditions_failed` with fixes | AGT-O-14 | 1 |
| CI report | `service:ci` on untrusted-evaluation workers; per-Proposal namespace | Agents cannot write it | AGT-O-14 | 1 |
| Risk classes | Deterministic from diff, target and integrity flags | — | AGT-O-14 | 1 |
| Separation of duties | Chain from server lineage; R3 and R4 need a human outside it | `propose.self_review_forbidden` | AGT-O-7 | 1 |
| Auto-merge | R0 and R1 only, clean contexts, verifier, two classes, quiet period | `propose.policy_unsatisfied` | AGT-O-14 | 2 |
| Agent freeze | All agent writes stop within 5 s (target) | — | AGT-O-7 | 1 |
| Provenance | Signed in-toto statements for every Change | Unsigned Change refused | AGT-O-10 | 1 |

## Labels and injection defence

Prompt injection is not solved: Meta calls it "a fundamental, unsolved weakness in all LLMs" [S28], and OWASP lists it first among LLM application risks [S29]. Crucible therefore relies on no model resisting it. Authority comes only from authenticated principals and grants, every value carries `Labels`, and the server enforces every boundary.

| Threat (OWASP agentic risk [S30]) | Primary controls |
| --- | --- |
| Instructions in imported text, datasheets, comments, documents or textures (ASI01) | Three instruction sources (D-AGT-18); handles; context labels; extraction |
| Misuse of a legitimate method (ASI02) | Scopes, write sets, risk classes, Act approvals |
| Stolen or escalated credentials (ASI03) | Sender-constrained tokens; delegation grants (D-AGT-28) |
| Malicious servers, skills or packages (ASI04) | Approved skill manifests; signed packages; external MCP servers off by default in hosted sessions, and stdio ones only in PLT's sandbox |
| Code execution (ASI05) | Only Ingot and determinized Wasm components; Proposal CI in single-use microVMs |
| Poisoned memory, spoofed messages (ASI06, ASI07) | No shared agent memory; no direct messaging (D-AGT-14) |
| Cascading failures (ASI08) | Budgets, attempt limits, merge-queue CI, freeze |
| Over-trust by reviewers (ASI09) | Risk classes, verifier reports, server-generated approval pages |
| Rogue agents and exfiltration (ASI10) | Write-down, clearances, egress only through Acts, audit |

### Instruction authority and untrusted content

**Decision D-AGT-18:** Instruction authority comes from three sources only: the delegating human's goal, role skills whose manifest digest a `policy:admin` approved, and first-party std and `crucible::` documentation built by the hermetic builder. Everything else is data: the API returns untrusted free text only as `ExternalText` handles with origin and untrusted typed values only as `ValueRef` handles, and a human merge endorses structure and typed values, never free text. *Why:* defences with provable resistance constrain an agent after it ingests untrusted input [S25]; endorsement by merge made injected comments trusted forever (R5-02); publisher verification establishes identity, not safe text (R5-13). *Rejected:* detection classifiers or spotlighting as primary controls (probabilistic; kept as monitoring signals); trusting text from verified publishers or protected branches. (revised in round 2)

Untrusted origins include imported files, supplier, catalog and web content, all third-party package text, extraction output and attachments to agent requests. Free-text spans are comments, doc comments, string literals, description templates and identifiers neither compiler-produced nor human-typed. `repo` records for each span the integrity of the context that wrote it. Read and Inspect methods return a span as a handle when its author is outside the reader's delegation chain or its integrity is untrusted.

A span becomes trusted only through `propose.endorse_text`, a human action that shows it verbatim with invisible and bidirectional characters highlighted. Importers generate neutral identifiers such as `part_017` and keep original names as `external(...)` values, which are never endorsed.

### Context labels and write-down

**Decision D-AGT-24:** Every model context carries a label, the join of the `Labels` of every value returned to it (contract section 7.6). Reading free text or images sets `instruction_tainted`; reading any untrusted value sets `data_untrusted`. Every write carries at least the context's label, a write to a lower-labelled destination fails with `label.write_down` unless a declassification record names it, and untrusted typed values travel by `ValueRef` so their labels follow exactly. *Why:* a model context is a derivation path that Kiln never sees, so ITAR content read in one repository could otherwise be written unlabelled into another (R5-01). *Rejected:* labelling only Kiln derivations; treating untrusted typed values as non-tainting, since they steer edits and re-enter as trusted literals.

An external host gets a fresh label only through a fresh authorization grant. Writes are edits, Proposals, comments, reviews, exploration records and Act payloads.

### Taint and the Rule of Two

Meta's Rule of Two names three properties: processing untrustworthy inputs, access to sensitive systems or private data, and the ability to change state or communicate externally. An agent should hold at most two in one session [S28].

| Context | Edit own branch | Propose | Merge or auto-merge | Prepare Acts |
| --- | --- | --- | --- | --- |
| Clean | Yes | Yes | Subject to policy | Yes |
| `data_untrusted` | Yes | Yes; at least R2 | No auto-merge | Yes; the plan carries the flag |
| `instruction_tainted` | Yes | Yes; at least R3 | No | Yes; the approval page lists the taint sources |

An `instruction_tainted` context holds all three properties in a narrow form: its only state changes are its own branch, Proposals that humans review and Acts that assigned humans approve. The rule calls for supervision when all three are present [S28], and review and approval supply it; KLN's threat model points here (R5-30). Flags never clear inside a context.

### Quarantined extraction and external hosts

Roles that need facts from untrusted documents use the Dual LLM pattern [S25]. `std::agents::extract` runs server-side: a model with no tools and no other context fills an Ingot record of quantities with units, enums and bounded strings from fixed templates, and the output is schema-validated, range-checked and labelled `data_untrusted`. Microsoft's FIDES uses a tool-free quarantined model the same way [S27]; extraction ships in phase 2 with the hosted crew, and until then external text is available only as handles.

**Decision D-AGT-25:** For every client except the hosted crew, `read.external_text` returns only quarantined typed extracts, never raw text. Raw reads need the per-client flag `allow_raw_external`, set under D-AGT-27, which records the host's tool inventory and is refused on repositories above `internal`. The hosted crew's web fetches run in a tool-free context and return typed extracts, and no URL may be built from context data. *Why:* a host with its own fetch, mail or chat tools completes the lethal trifecta outside Crucible's sight once its model reads raw untrusted text (R5-07). *Rejected:* relying on clearance at the response alone; trusting hosts to sandbox their own tools.

`server/discover` states this rule in the server instructions.

### Write sets, protected paths and two-person rules

Write sets confine edits to globs, and protected branches (`main`, `release/*` and any a policy names) reject direct writes from every principal. Protected paths (`oracles/**`, policy files, lockfile behavior-version pins, recipient records) reject agent writes outside Proposals and raise a Proposal to R3 or R4.

**Decision D-AGT-27:** Two distinct humans approve each of these, and for label-related items one holds `export_officer`: clearing an endpoint, client or recipient for `confidential` or any export control; declassification; Cedar changes that widen access; auto-merge policy; recipient-record changes; oracle and protected-path changes. Policy Proposals from a context with either integrity flag are refused, and break-glass access exists with a mandatory review afterwards and an alert to every administrator. *Why:* one malicious, coerced or phished administrator could otherwise export a whole ITAR programme in a single action (R5-15). *Rejected:* single-administrator control; no break-glass, which pushes people around the controls during outages.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Instruction authority | Three sources; everything else data | Injected instructions change no consequential action | AGT-O-8 | 0 |
| Free-text handles and endorsement | Span-level integrity; per-span human endorsement | `auth.human_only` | AGT-O-8 | 1 |
| Context labels and write-down | Join of every returned value; writes carry it; `ValueRef` handles | `label.write_down` | AGT-O-17 | 1 |
| Quarantined extraction | Tool-free, templated, schema-validated | Invalid output dropped and reported | AGT-O-8 | 2 |
| External-host raw reads | Extracts only; `allow_raw_external` at `internal` or below | `label.raw_external_forbidden` | AGT-O-8 | 1 |
| Protected paths | Agent writes only through Proposals; R3 or R4 | `edit.protected_path` | AGT-O-7 | 0 |
| Two-person rules | Two humans; an export officer for label items; break-glass | `propose.policy_unsatisfied` | AGT-O-7 | 1 |

## Clearance, egress and data protection

### Endpoint and client clearance

**Decision D-AGT-19:** Every model endpoint and every external client carries a clearance, a bound in the label lattice granted under D-AGT-27, and a context receives only values that its clearance and its human's clearance both satisfy. Clearance above `internal` requires the hosted crew, or a pre-registered confidential client that authenticates with `private_key_jwt` [S59] from a hardware-backed key and sends its model traffic through Crucible's model gateway. The gateway enforces the endpoint allowlist and records the model actually used. *Why:* Client ID Metadata Documents cannot prevent localhost impersonation by themselves [S55], and a client identity says nothing about where a host forwards content (R5-08). *Rejected:* clearance by Client ID Metadata Document alone; trusting hosts to filter; redaction by a model. (revised in round 2)

`Declared` endpoints are never cleared above `internal` or for any export control, and an unattested client asking for more receives `label.client_unattested`. Unregistered clients get the policy default, `internal` unless set lower. The hosted crew and the gateway arrive in phase 2, so phase 1 agent contexts stay at `internal` and below.

Crucible provides mechanisms; the organization decides what is lawful. Two US carve-outs show what clearance must express:

- Under the EAR, sending or storing unclassified technology is not an export when it is end-to-end encrypted with FIPS 140-2 or successor modules and not intentionally stored in a Country Group D:5 country [S49].
- Under the ITAR, the data must be unclassified, end-to-end encrypted with FIPS 140-2 modules or AES-128 strength, neither sent to nor stored in a §126.1 country, and not sent from one [S50][S52]. No third party may hold the means of decryption, and the recipient must be the originator, a US person in the United States or otherwise authorized [S52].

An ITAR release includes oral or written exchanges with foreign persons [S53]. A hosted model provider decrypts prompts, so the third-party condition does not obviously hold for it [unverified: legal interpretation; not legal advice]. Export-controlled content is therefore cleared only for local models or endpoints inside the organization's own boundary.

### Exfiltration channels

| Channel | Control |
| --- | --- |
| Context of an uncleared endpoint or client | Clearance at the response (D-AGT-19) |
| Writes into a lower-labelled repository | Write-down rule (D-AGT-24) |
| Bytes leaving the tenant | The data-release Act family (D-AGT-30) |
| An external host's own tools | Extracts only (D-AGT-25) |
| URLs in agent output | Inert text unless allowlisted; external images never load in review |
| Hosted crew runtime | Egress only to the API, cleared endpoints and quarantined fetches |
| Read volume | Bytes read per context against the role baseline; alert and optional freeze |

### Audit and personal data

Audit entries live in KLN's transparency log, with its retention rule and verifier (R5-39), and in KLN's signed append-only audit log in phase 1. This tab owns the schema: pseudonymous principal, delegation chain, session, method, argument digest, status, labels, cost, client and trace, with full content only for Act plans, approvals and policy changes.

**Decision D-AGT-32:** Audit entries, provenance and signature records hold pseudonymous principal ids. A separate identity directory maps ids to names under a per-person key that can be crypto-shredded, except under documented legal holds such as Part 11 retention or litigation. Transcripts and API logs keep their own retention, 12 months by default, separate from release records. *Why:* append-only logs with names forever have no erasure path, while GDPR Article 17(3) permits retention for legal obligations and legal claims [S56] (R5-27). *Rejected:* names in every entry; one seven-year retention for everything.

Agent presence and per-person activity analytics are organization settings with a works-council mode, because German law gives works councils co-determination over devices designed to monitor employees' behaviour or performance [S57]. Crucible ships records-of-processing entries, a data protection impact assessment template and the list of hosted model providers as sub-processors with their regions and retention terms.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Endpoint and client clearance | Lattice bounds granted by two humans | `label.exceeds_clearance` naming a cleared endpoint | AGT-O-17 | 1 |
| Attested clients and model gateway | `private_key_jwt` from a hardware key; gateway records the model | `label.client_unattested` | AGT-O-17 | 2 |
| Export-control defaults | Controlled content only to local or in-boundary endpoints | `label.exceeds_clearance` | AGT-O-17 | 1 |
| Egress monitoring | Read-volume baselines per role | Alert; optional freeze | AGT-O-8 | 2 |
| Audit schema | Entries in KLN's log; digests except Acts and policy | Missing entry fails the call | AGT-O-20 | 0 |
| Personal data | Pseudonymous ids; crypto-shreddable identities; 12-month transcripts | Legal hold blocks shredding, recorded | AGT-O-20 | 1 |

## Acts and approvals

Act methods cover every effect outside Crucible, and every Act is two-phase (contract section 2). Each class declares its family, plan schema and reversibility.

| Act class | Family | Effect | Reversibility | Phase |
| --- | --- | --- | --- | --- |
| `release` | Record | Signed release tag | Superseded by a change order | 1 |
| `grant_deviation` | Record | A deviation against a release | Revocable going forward | 2 |
| `yank_package`, `deprecate_package` | Record | Registry status | Yank never deletes | 2 |
| `send_to_supplier` | Data release | Files for quotation or production | Irreversible | 1 |
| `export` | Data release | Repository archive, release bundle, Git mirror | Irreversible | 1 (archive, bundle), 2 (Git mirror) |
| `request_quote`, `order` | Data release | RFQs and purchase orders | Orders compensable | 2 |
| `share_external`, `notify_external` | Data release | Sharing with another organization; outside messages | Access revocable | 2 |
| `publish_package` | Data release | A public registry version | Yankable | 2 |
| `publish_passport` | Data release | A digital product passport (MFG) | Superseded | 3 |
| `send_to_machine` | Physical effect | A posted NC program to a DNC queue or program store | Irreversible once run | 2 |
| `store_machine_job` | Physical effect | OPC UA job `Store` only | Revocable before start | 2 |
| `send_print_job`, `start_print` | Physical effect | A print job; a restricted start | Cancellable | 2 |
| `send_robot_program` | Physical effect | A robot program to its controller | Irreversible once run | 2 |
| `run_rig_test` | Physical effect | A test on an `unattended_safe` KLN rig | Irreversible | 2 |

**Decision D-AGT-20:** Every Act is two-phase. `act.prepare` produces a deterministic `ActionPlan` whose digest is the approval subject. `act.commit` creates an approval request that Cedar policy assigns to named approvers and delivers only to their Crucible inbox. The model receives `act.approval_pending` with a request id, never a URL, and approvers decide on one server-generated page after phishing-resistant WebAuthn user verification [S60], on desktops and tablets only. *Why:* a URL that reaches a model can be forwarded to a busy approver, and MCP itself requires servers to verify who opens an elicitation URL [S54] (R5-04). *Rejected:* URL-mode elicitation through the agent's client; approval by any holder of authority; form elicitation in the host; standing pre-approvals. (revised in round 2)

```rust
pub struct ActionPlan {
    pub digest: Sha256,                  // over the canonical plan; the approval subject
    pub class: ActClass,
    pub effects: Vec<Effect>,            // e.g. SendFiles { recipient, files: [(server_name, sha256, labels)] }
    pub recipients: Vec<RecipientId>,    // KLN RecipientRecords
    pub subject: Option<ObjectId>,       // release: ApprovalSubject; programs: program and evidence
    pub authorization: Option<ExportAuthorizationId>,
    pub labels: Labels,                  // payload joined with the preparing context
    pub requested_by: Vec<PrincipalId>,
    pub expires: Timestamp,              // default 24 h
}
```

The approval page is the only approval surface; UIX renders it on desktop, web and tablet, and the MCP Apps viewer is read-only. It shows:

- file names generated from item number, revision, format and release tag, never chosen by the plan's author;
- a server-rendered thumbnail and a content summary of Items, labels and bytes;
- each recipient's verification and screening dates, with a banner when the record changed in the last 7 days;
- a diff against the last approved plan of the same class to the same recipient;
- the session's purpose, marked as agent text, and the context's integrity flags with their sources.

Anyone else who opens a request sees "not assigned to you", and push notifications carry no content. A denial blocks re-preparing a plan to the same recipients for 24 h and offers "report as suspicious", which freezes the session.

`act.prepare` rejects payload text containing invisible characters, Unicode tag characters (U+E0000 to U+E007F), bidirectional controls or zero-width characters. A plan that changes after approval fails with `act.plan_changed`, and approvals are single-use.

A release plan's digest covers the `ApprovalSubject`'s `ObjectId`, the tag and the effectivity, never the `ChangeId` or the CI report. A rebase or CI re-run that leaves the subject unchanged therefore keeps its approvals, and a change order's approvals are exactly these (R3-16, R3-22). Every approval of a release or an R4 Act becomes a KLN signature record with meaning, printed name and time (R5-21).

[[DIAGRAM diagrams/09-agents-act-sequence.jsx: Act sequence · two-phase commit with the approval out of band]]

**Decision D-AGT-30:** Every byte that leaves a tenant goes through one Act family, `release_data { recipient, payload, purpose, authorization }`, which AGT owns. KLN runs its checks as one stage at `act.commit` and records the result (D-KLN-40): labels against the recipient's attributes, restricted-party screening, an export authorization record (licence number, licence exception or exemption) for any export control, a watermark record, expiry and audit. Recipients are KLN `RecipientRecord`s, verified out of band and screened, so a recipient that appears only in agent text is refused with `act.recipient_unverified`. *Why:* six egress paths with different controls invite the weakest (R5-06), and a recipient changed through an injected "our address has changed" email would redirect every later RFQ (R5-05). *Rejected:* per-path controls; recipient records changed by ordinary Proposals.

Recipient-record changes follow D-AGT-27, cannot come from a context with either integrity flag, and take effect after 24 h with notice to the previous contact (KLN). Agent writes on branches shared with another organization need `act:share_external` and are refused to `instruction_tainted` contexts. Webhooks carry thin payloads without design content (ECO), so they are not data release.

**Decision D-AGT-31:** Physical-effect Acts only transfer data to a device, or start a print or a rig test under restrictions. Crucible never issues cycle start, resume, jog, `Start` or `StoreAndStart` to machine tools, robots, lasers, presses or furnaces; a person starts them at the device. Agents may prepare transfer Acts, only assigned humans approve them, and no agent or remote approval can give an on-site confirmation. *Why:* an approved plan or a compromised approver must never start motion where nobody is standing (R4-01, R5-18). *Rejected:* remote starts through OPC UA job methods; transfers committed by agents; a remote build start (MFG, round 1).

- `send_to_machine` delivers an approved, hash-bound program to a DNC queue or program store. Its subject is the posted program and its simulation evidence; MFG's gateway re-verifies header, tool lengths and offsets, and edited programs return as Proposals.
- `start_print` exists only for printers whose profile declares thermal-runaway protection and enclosure or smoke detection, needs an on-site confirmation at the printer or with a site-bound key, and is off by default.
- `run_rig_test` runs on KLN's hardware runner, only for rigs under an `unattended_safe` site policy, after an Approval of the test plan's digest (contract 7.1, 7.6).
- Machine data collection is a Read, `read.machine_data`.

These classes ship in phase 2 with MFG's transfer capabilities (contract section 13.2).

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Two-phase Acts | Deterministic plan digest; commit after an assigned Approval | `act.plan_changed`, `act.denied` | AGT-O-9 | 1 |
| Approval requests | Cedar-assigned; inbox only; request id to the model; WebAuthn; no phones | "Not assigned to you"; phone refused | AGT-O-9 | 1 |
| Approval page | Server-generated names, thumbnail, summary, recipient dates, diff, purpose | — | AGT-O-9 | 1 |
| Approval limits | Three pending; 24 h block after denial; report freezes the session | `act.denied_cooldown` | AGT-O-9 | 1 |
| Character rejection | Invisible, tag, bidirectional and zero-width characters refused | `act.payload_rejected` | AGT-O-9 | 1 |
| Release Acts | Digest over the approval subject; KLN signature records | `act.plan_changed` only when the subject changes | AGT-O-9 | 1 |
| Data-release family | Labels, screening, authorization, watermark, expiry, audit on every egress | `act.recipient_unverified`, `label.exceeds_clearance` | AGT-O-22 | 1 |
| Physical-effect Acts | Transfer only; restricted `start_print` and rig tests; on-site confirmation | `act.onsite_required` | AGT-O-21 | 2 |

## Model independence

Every guarantee lives in the server, so models differ in how well they work, never in what they may do. An external host owns its model loop while Crucible enforces every call; the hosted crew runs Crucible's own loop inside the deployment.

**Decision D-AGT-21:** The hosted crew calls models through one Rust trait, `ModelEndpoint`, with adapters for major hosted APIs and local OpenAI-compatible servers. Crucible does not use MCP Sampling. *Why:* MCP 2026-07-28 deprecates Sampling and advises integrating with provider APIs directly [S2]; one trait keeps provider choice a configuration decision. *Rejected:* Sampling through the client (deprecated); a single provider (founder requirement and air-gapped installs).

```rust
pub trait ModelEndpoint: Send + Sync {
    fn record(&self) -> &EndpointRecord;            // weights digest or dated provider version, region
    fn capabilities(&self) -> &ModelCapabilities;   // tool calling, vision, context, structured output
    fn clearance(&self) -> &Labels;                 // the bound granted under D-AGT-27
    async fn complete(&self, req: CompletionRequest) -> Result<CompletionStream, ModelError>;
}
```

An `EndpointRecord` pins the weights digest of a local endpoint or the dated model version of a hosted one, and weights distributed through the registry are signed like packages (R5-44). An endpoint qualifies for a role by passing that role's suite of golden tasks; qualification binds to the record, so a change forces re-qualification.

| Missing capability | Degradation |
| --- | --- |
| Vision | `visible_summary`, structured marks and `inspect.describe`; the role runs only if qualified in text-only mode |
| Native tool calling | JSON-mode calling with schema validation and up to two repair retries; endpoints with neither are not qualified |
| Long context | Smaller pages, outlines before source, concise detail |
| Endpoint unavailable | Backoff, then the next qualified endpoint in the role's list, recorded in provenance |
| No qualified endpoint | `crew.no_qualified_endpoint` with the qualification results; never a silent downgrade |

Model outputs are not deterministic, so identical behavior is claimed only for Crucible's side. Every hosted-crew model call stores a replay record in CAS, so benchmarks and incident reviews can replay a session's API calls exactly.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| External hosts | Any MCP 2026-07-28 client under server enforcement | Typed `auth` and `label` errors | AGT-O-1 | 0 |
| Hosted crew | `apps/crew` over the public SDK; per-tenant instances | `crew.no_qualified_endpoint` | AGT-O-15 | 2 |
| Endpoint records | Weights digest or dated version; re-qualification on change | Unqualified endpoint refused | AGT-O-10 | 2 |
| Qualification and degradation | Per-role suites; declared degradations | Never a silent downgrade | AGT-O-15 | 2 |
| Replay records | Every crew model call in CAS | — | AGT-O-10 | 2 |

## Benchmarking and training data

Agent quality is measured, versioned and gated like any other feature. The harness, suites and graders live in `oracles/agents/`; held-out suites live outside every repository agents can read.

| Suite | What it measures | Use |
| --- | --- | --- |
| Text2CAD-Bench | Text to parametric CAD at four levels; 600 examples [S16] | External comparison on exported geometry |
| CADPrompt | 200 prompts; point-cloud distance, compile success [S17] | External comparison |
| CADTestBench | Text to CAD verified by executable tests [S18] | Reference for check-based grading |
| MUSE | Manufacturable assemblies; strongest models scored 19–21% on fine-grained criteria [S19] | Phase 2 and later |
| Golden-product tasks | Create, edit, fix a check, add a study, DFM, CAM, change order; at least 50 per product (target) | Primary metric and release gate |
| Held-out set | The same on unseen products; at least 200 by phase 2 (target) | Overfitting control |
| Injection suite | Planted instructions in imports, comments, merged doc comments, identifiers, templates, embossed geometry and textures; at least 100 per release (target), AgentDojo methodology [S34] | Security gate |

Crucible reports adapted variants of public benchmarks and reimplements Text2CAD-Bench's metrics from the paper, since its evaluation code was unreleased [S16]. Golden tasks ship with a starting Change, a goal, hidden acceptance checks, a reference solution and forbidden actions, and are graded by checks in `service:ci` in two platform classes. A model judge scores only documentation and requirement-text fidelity, with a 0.0–1.0 rubric [S33], another model family and a human calibration set each release.

Metrics are task success, pass^1 and pass^4, checks passed, edit minimality, query robustness, review acceptance, verifier catch rate, cost per success, injection resistance and safety violations. τ-bench found pass^8 below 25% in its retail domain for state-of-the-art agents [S35], so reliability across trials is gated.

Every release and every change to `std::agents`, `apps/crew` or the MCP surface reruns golden tasks and the held-out set on every qualified endpoint, three trials per task. The gate fails if success drops by more than 2 points (target) at 95% confidence by paired bootstrap, or if any injection succeeds. Red-teaming adds adaptive attacker models [S34], human red teams before each gate, tripwires and, from phase 3, a public bounty [unverified: terms to be set].

Models adapt through context first and are fine-tuned only where measurement shows a gain. The generator emits valid Ingot programs, edits with template descriptions, repairs of injected errors and observations paired with facts; every item builds, and the corpus is reproducible from its seeds. CAD-Recode trained on one million procedurally generated CAD sequences [S20].

| Source | Terms | Use |
| --- | --- | --- |
| Fusion 360 Gallery Dataset | Non-commercial research only; terminable by Autodesk [S21] | Never in anything that ships, in any tab |
| ABC dataset | Licensed by reference to Onshape's terms, which vary by document date and LICENSE tab [S22][S23] | Excluded until per-document filtering is verified |
| DeepCAD and derivatives | Built from ABC [unverified] | As ABC |
| Public CAD benchmarks | Licences not stated on the pages opened [S16][S17][S18][S19] | Evaluation only, after licence review |
| Procedural data, std, golden products | Crucible's own | Unrestricted |
| Customer data | Owned by the customer | Opt-in only |

**Decision D-AGT-22:** Every model that ships from any tab trains and adapts only on procedural data, std and golden products, data with verified commercial-use licences, and customer data under explicit opt-in. Cross-tenant training admits only items labelled `public` or whose `DataLicence` explicitly permits ML training under a contract addendum, never `confidential` items or third-party Assets, and per-tenant adaptation uses dedicated weights never served to another tenant. *Why:* weights inherit data obligations, the Fusion 360 Gallery licence forbids commercial use [S21], and a company's geometry and edit patterns are its intellectual property (R5-28, R5-33). *Rejected:* research-use exceptions for shipped models, including ECO's segmentation models; scrubbed but confidential corpora; scraping public CAD models. (revised in round 2)

Opt-in is off by default and set per repository by two humans (D-AGT-27), with eligibility computed per item from labels and licences. Before a shared model ships, the corpus is deduplicated and planted canaries must not be extractable. Withdrawal removes items and takes affected shared models out of service within 30 days, and corpora exclude principal identities and free-text comments.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Benchmark harness | Suites above, graded by checks in two classes | — | AGT-O-15 | 1 |
| Release gate | Three trials per task per endpoint; 2-point drop at 95% or any injection fails | Release blocked | AGT-O-15 | 1 |
| Injection suite | Planted instructions across every text and image channel | Gate fails on any success | AGT-O-8 | 1 |
| Verifier efficacy | Planted-defect catch rate | Gate fails below target | AGT-O-19 | 2 |
| Procedural corpus | Items build; reproducible from seeds | Failing items excluded | AGT-O-23 | 2 |
| Training eligibility | Per-item labels and licences; canary tests; 30-day withdrawal | Ineligible items excluded and reported | AGT-O-23 | 3 |

## Agent-facing documentation

**Decision D-AGT-23:** All agent-facing documentation is generated from the Rust method types, Ingot doc comments and the error catalog, pinned to versions and compiled in CI. Every example is built and its checks evaluated, a page whose example fails blocks the release, and `read.docs` answers for the repository's lockfile, never the latest release. *Why:* stale docs teach agents wrong APIs, and version-pinned answers match the code the agent edits. *Rejected:* hand-written agent docs (drift); retrieval over the web (unversioned, untrusted).

Crucible publishes an API reference per method, a std reference, an error catalog with reproducing examples and fixes, runnable examples, skills and a `llms.txt` index. Pages state units, preconditions and failure modes in about 2,000 tokens (target), and doc changes are benchmarked like code, since better tool descriptions measurably help agents [S31].

A grant exposes at most 60 tools, and a new method needs a benchmark gain over composing existing ones [S31]. Responses use readable paths such as `gearbox/input_shaft[1]` beside `EntityId`s, deprecations carry a machine-applicable fix for 12 months, and CI fails when a public std item lacks a doc comment, an example or units.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Generated references | Methods, std and errors from source, pinned to versions | A failing example blocks the release | AGT-O-16 | 0 (errors), 1 (std) |
| Lockfile-pinned answers | `read.docs` for the repository's lockfile | `docs.not_found` with nearest matches | AGT-O-16 | 1 |
| Tool surface | At most 60 tools per grant; group prefixes | A new method without benchmark gain is refused in review | AGT-O-15 | 1 |

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Agent protocol | MCP 2026-07-28 with Tasks and Skills [S1][S2][S4][S8] | Fusion MCP and Fusion Data MCP [S13][S14]; Onshape FeatureScript MCP [S24] | Adopt; one catalog behind every transport, with a published approval model that neither Autodesk announcement details (D-AGT-1, D-AGT-2) | AGT-O-1; golden transcripts pass on 5 MCP hosts (target) |
| Conversational CAD agents | Code as the medium, selection awareness, four-view self-review [S11][S12] | Zoo Zookeeper [S11][S12]; NX Copilot answers with sources but does not act [S42][S43] | Ingot, `session.presence`, `Grid4`; independent verification instead of self-review alone | AGT-O-15 |
| Tool and response design | Consolidated, namespaced tools; concise responses; actionable errors [S31][S32] | Claude Code's 25,000-token limit [S31] | At most 60 tools per grant; `detail`; a 20,000-token cap | Tokens per successful task |
| Errors and retries | RFC 9457 [S45]; tool execution errors [S3]; Idempotency-Key [S46] | — | D-AGT-6, D-AGT-7 | First fix resolves at least 60% of errors with fixes (target); AGT-O-5 |
| Delegated identity | MCP's OAuth 2.1 profile [S6]; token exchange [S47]; DPoP [S58] | — | Delegation grants, sender-constrained tokens, chains from server lineage (D-AGT-28) | AGT-O-7, AGT-O-24 |
| Prompt-injection defence | Design patterns [S25]; CaMeL, 77% of AgentDojo tasks with provable security against 84% undefended [S26]; FIDES labels [S27]; Rule of Two [S28] | CaMeL [S26] | Context labels and write-down, three instruction sources, Plan-Then-Execute, Dual LLM extraction, approved Acts (D-AGT-18, D-AGT-24, D-AGT-25). Deviation: no CaMeL interpreter around every role. *Reason: maturity;* design loops interleave reading and editing, so phase 3 evaluates one for `instruction_tainted` roles | Zero attacker-chosen consequential actions; utility under attack within 10 points of clean (targets) |
| Visual grounding | Set-of-Mark prompting [S36] | Zookeeper's multi-view snapshots [S11] | Marks with structured maps, `Grid4`, text summaries (D-AGT-9) | Entity-selection accuracy at least 95% (target) |
| Snapshot comparison | ꟻLIP perceptual difference [S62] | — | ꟻLIP thresholds against a pinned renderer image | AGT-O-3 |
| Design verification | CADCodeVerify [S17]; executable tests [S18] | CADCodeVerify [S17] | Checks plus a mutating verifier (D-AGT-12) | Catch rate at least 90% by phase 2 (target, AGT-O-19) |
| Orchestration | Orchestrator-workers [S32]; parallel subagents [S33] | Anthropic's research system [S33] | Validated plans, branches, a merge queue; one agent by default (D-AGT-13) | Success and cost against one agent |
| Expensive optimization | qLogNEHVI [S37][S38]; hypervolume knowledge gradient [S39]; scaled priors [S40] | BoTorch 0.18.1 [S38] | `std::explore` in Rust (D-AGT-15) | Hypervolume within 5% of BoTorch (target) |
| Cheap optimization | NSGA-II and NSGA-III [S41] | pymoo 0.6.2 [S41] | The same in `std::explore` | Hypervolume against pymoo |
| Text-to-CAD and editing | Text2CAD-Bench [S16], CADPrompt [S17], CADTestBench [S18], MUSE [S19], CadEval [S44] | Text2CAD-Bench L1 geometric prompts: GPT-5.2, invalidity 11.1%, IoU 0.59 [S16] | Ingot agents in check-driven loops | Adapted L1: invalidity at most 5%, IoU at least 0.75 (target; not directly comparable) |
| Reliability | pass^k [S35] | — | pass^1 and pass^4 per suite | Release gate (AGT-O-15) |
| Training data | Procedurally generated CAD programs [S20] | CAD-Recode [S20] | An Ingot generator whose items build (D-AGT-22) | Gain on the held-out set |
| Provenance | in-toto Statement v1 [S48] | — | Signed `ChangeProvenance` | AGT-O-10 |
| CAM assistance | Strategies accepted step by step [S15] | CloudNC CAM Assist [S15] | CAM programmer gated by collision and gouge checks | At least 50% of golden programs accepted unedited (target) |

## Platform notes

- **Desktop, every Tier 1 OS.** `crucible mcp` runs on stdio with the user's keychain credential [S6]; local SDKs use a Unix domain socket or named pipe, never an unauthenticated localhost port [S7].
- **Browser, Tier 1.** Browser agents use the TypeScript SDK over Streamable HTTP to a team server; the page links `core/api` as Wasm for the user's own edits and runs no models.
- **Servers.** `apps/mcp` and `apps/crew` ship as Linux containers for x86-64 and ARM64, routed by `shard_key`; Proposal CI runs in untrusted-evaluation microVMs.
- **Air-gapped installs.** Local endpoints, bundled docs, skills and suites, qualification on site, no external MCP servers.
- **Tier 2.** Tablets review and approve Acts with WebAuthn platform authenticators.
- **Snapshots.** Byte identity holds only on the pinned CI renderer image, a container with a pinned lavapipe build and fixed vector width and CPU capabilities [S61]; elsewhere ꟻLIP thresholds apply.
- **Portability.** Python and TypeScript SDKs are pure-language; the Rust SDK builds for every Tier 1 target, `wasm32` included. Paths are repository-relative, forward-slash and NFC, and no agent function needs a GPU.

## Interfaces with other subsystems

### What AGT provides

| To | Provides | Types |
| --- | --- | --- |
| All tabs | The `api` catalog; sessions; labels at the boundary; budgets; idempotency; errors; the audit entry schema | API method |
| ING | `SourcePatch` application in `edit.apply`; `read.*` and `inspect.describe` returning free-text spans as handles | API method |
| KLN | Admission; `Budget` and `PriorityClass` fields; the `release_data` Act family (D-AGT-30); context labels on writes; Proposal fields, risk classes, auto-merge decisions; the approval page's content (D-AGT-20) | `Budget`, `Proposal` |
| UIX | `inspect.render` and `inspect.ask_render`; Proposals with plans, verifier reports, risk classes and provenance; open questions; `ActionPlan`s and approval requests; agent event streams and `session.control` | `Proposal`, `ActionPlan`, `ChangeProvenance` |
| MFG | Physical-effect, `request_quote` and `publish_passport` Act classes, approved over posted programs and their evidence; `read.machine_data`; Proposals; the CAM programmer role (phase 2) | Act class |
| ELX | Datasheet extraction into ELX's records, labelled `data_untrusted`; budget caps for long tool runs | Proposal |
| ECO | Catalog entries for ECO's methods; Act classes and the `release_data` family; `ExternalText` and instruction authority; untrusted-snapshot rules (D-AGT-26); audit; MCP subscriptions; `std::agents` and `std::explore` | Package, Act class |
| PLT | Message types and canonical JSON; the `ApiError` shape that `Guidance` errors map into; `Usage` as the resource record | `Usage`, `ApiError` |
| Every tab that ships a model | The training-data rule (D-AGT-22) | — |

### What AGT requires

| From | Requirement |
| --- | --- |
| ING | Diagnostics with `SourcePatch` fixes; the formatter; metadata for tool schemas; doc comments and templates; `ExternalText` and free-text span classes; `CheckOutcome` and the decision rule; `#[was]`; `ING-L-FragileSelector` |
| KLN | Evaluations with priority classes, safe points, work budgets and Aborts; labels as memo outputs and write-down at `repo`; Changes, semantic merge and diffs; span-level integrity; `RecipientRecord`s; the `release_data` stage at commit (D-KLN-40); declassification and signature records; the audit log in the transparency logs; two worker pools; lifecycle methods; Cedar |
| ANV | Entity inspection with provenance; `Query` resolution with ranked fixes and `RankSwap`; exact measures and sections; geometry diffs (volumes added and removed, Hausdorff deviation) |
| FLX | Study Evaluations; regularized goals; `ErrorBudget`s and zones; plan explanations (`SolvePlan`); cost estimates; Field sampling; gradients and surrogates for `std::explore` |
| COV | Validity envelopes; the coverage map and limit records; typed `ValidityError`s with escalation |
| UIX | The headless renderer with `RenderProfile`; the review view; the approval page; steering controls |
| MFG | Act payloads for its Act classes; DFM rules and machinability reports; CAM; cost with intervals; `MfgError` fixes; the machine gateway that re-verifies programs and captures edits; printer profiles |
| MEC | Std features with doc metadata; tolerance stacks; `SolveReport`s, `ContinuityReport`s and check Fields |
| ELX | Electronics checks; Proposals from placement, routing, matching and decoupling tools; datasheet record templates with page references |
| ECO | Signing for `std::agents` and `std::explore`; licence metadata; registry, event and archive behavior; importers emitting `ExternalText`; `release_data` members for archive, mirror, bundles, partners and connectors |
| PLT | The `api` transport, `cli` exit codes and `Usage` measurement; keychain; the OS sandbox for external MCP servers on stdio; WebAuthn authenticators |

## Oracles

Oracles live in `oracles/agents/`, readable but never writable by agents; held-out suites and tripwires live outside it.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| AGT-O-1 | MCP, Skills and schema conformance | Tools and `structuredContent` validate; skills match manifests; fuzzed requests yield typed errors; Tasks, polling and SDK streams give identical results |
| AGT-O-2 | SDK parity | Golden transcripts give byte-identical canonical JSON through every SDK and raw MCP |
| AGT-O-3 | Observation determinism | Scene graphs and descriptions identical across classes; snapshots byte-identical on the pinned image, elsewhere mean ꟻLIP at most 0.05 (target) |
| AGT-O-4 | Description integrity | Every number maps to a fact; perturbing a fact changes the text; third-party phrasing appears only as handles |
| AGT-O-5 | Idempotency | Injected drops and duplicates yield zero duplicate Changes or Acts |
| AGT-O-6 | Concurrency | A TLA+ model checks; randomized multi-writer tests lose no update and catch every stale base |
| AGT-O-7 | Policy enforcement | A reference evaluator agrees with the server over scopes, methods, protection, labels, clearances, chains of depth 1 to 3 and two-person rules |
| AGT-O-8 | Injection resistance | Zero attacker-chosen consequential actions, including via merged doc comments, identifiers, templates, embossed geometry, textures and a reference host with a fetch tool; write-down and label laundering count as successes |
| AGT-O-9 | Act integrity | `act.commit` without approval, changed plans, replays, non-assignee approvals from forwarded links, author-chosen names, hidden characters, approval spam, phone approvals and chain-internal R3 or R4 approvals are refused; release and R4 approvals have KLN signature records |
| AGT-O-10 | Provenance | Every Change carries a valid signed statement with complete fields, including the endpoint record; tampering is detected |
| AGT-O-11 | Budgets and rate limits | Spend never exceeds a cap by more than one safe-point interval; per-principal limits hold |
| AGT-O-12 | Plans and leases | Invalid generated plans are rejected and valid ones pass; stale-lease writes are always rejected |
| AGT-O-13 | Exploration | Hypervolume within 5% of the references (target); equal seeds give identical synchronous sequences; failures counted |
| AGT-O-14 | Risk classes and auto-merge | A labelled corpus gets the expected classes; loosening and `instruction_tainted` changes are R3 or higher; no `data_untrusted` change is R1; auto-merge refuses everything outside policy |
| AGT-O-15 | Agent quality gate | Golden tasks and the held-out set meet the regression thresholds per release and endpoint |
| AGT-O-16 | Docs | Every example builds and its checks pass; every public std item has a doc comment, an example and units |
| AGT-O-17 | Clearance and write-down | Tripwires never reach uncleared contexts or lower-labelled repositories; undeclassified writes down fail; `Declared` endpoints get nothing above `internal` |
| AGT-O-18 | Query robustness | Scores agree with a labelled set of robust and fragile queries; seeded rank swaps inside declared ranges are reported as `RankSwap` |
| AGT-O-19 | Verifier efficacy | The planted-defect catch rate meets its target |
| AGT-O-20 | Audit | One entry per call in KLN's log; shredding an identity key leaves the log verifiable and the person unidentifiable |
| AGT-O-21 | Physical safety | No Act plan schema can express a machine start; `start_print` without on-site confirmation and `run_rig_test` on a rig outside an `unattended_safe` policy are refused; no agent or remote approval supplies on-site confirmation |
| AGT-O-22 | Data release | Every egress path runs the data-release checks; seeded failing recipients are refused; recent recipient changes show the banner |
| AGT-O-23 | Training data | Eligibility follows labels and licences; canaries are not extractable; withdrawals complete within 30 days |
| AGT-O-24 | Delegation grants | Exchange without a live grant, for non-agent scopes, or for Approvals or `policy:admin` is refused; tokens are sender-constrained |

## Phasing

No AGT capability appears in contract 13.4's shared phase table.

| Phase | AGT contribution to the gate |
| --- | --- |
| 0 | `core/api` types and schemas; Session, Read, Edit and core Evaluate methods; idempotency; errors and the docs pipeline; MCP server on stdio and HTTP; the Rust SDK; source-level descriptions; audit entries; policy enforcement. AGT-O-1, 4, 5, 6, 7, 16 and 20 green |
| 1 | GP1 and GP2 worked with agents through external MCP hosts: Inspect, Compare, Propose, CI reports and risk classes; context labels and write-down; `release`, `send_to_supplier` and `export` with the full approval flow; Rust and Python SDKs; three roles; the benchmark harness and injection suite. Golden tasks on GP1 and GP2 reach pass^1 ≥ 80% and pass^4 ≥ 60% on the best qualified endpoint (targets); AGT-O-8, 9, 17 and 22 green |
| 2 | Hosted crew, delegation grants, model gateway and extraction; TypeScript SDK; nine further roles; swarms; exploration; auto-merge; physical-effect and remaining data-release Acts. Swarm tasks on GP3 and GP4 beat the single-agent baseline at no more than 3× its cost (target); AGT-O-21 and 24 green |
| 3 | Hypervolume knowledge gradient; training opt-in with canary tests; a public bounty; an interpreter evaluated for `instruction_tainted` roles; `publish_passport`. Golden tasks on GP5 at the phase 1 thresholds (target) |
| 4 | Validation against physical test data with correlation checks. GP6 explorations confirm at least 3 Pareto-optimal variants at `SignOff` (target) |
| 5 and later | A compliance-evidence role; agents across organizations if A2A is adopted after review |

## Open questions

1. **Model attestation beyond the gateway.** Could signed provider receipts attest models used by hosts outside the gateway?
2. **Export control with hosted models.** Counsel must decide whether a hosted endpoint can meet the ITAR carve-out before any controlled clearance [S50][S52].
3. **R1 thresholds.** Are a 90% margin floor, 0.5 mm deviation and 1% cost increase right? Phase 2 review data sets them.
4. **ABC filtering.** Can per-document licence filtering be reliable enough [S22][S23]?
5. **Asynchronous exploration.** Is its throughput worth a non-reproducible default?
6. **Host support.** Will major hosts support Tasks and Skills by phase 1?
7. **Quarantine independence.** Must the quarantine endpoint come from another provider?
8. **Mutation cost.** What sampling bounds verifier cost on assemblies of 1,000 or more parts?
9. **Host-side tokens.** Should budgets include unverifiable token usage that hosts declare?
10. **Label granularity.** A token family shares one label, so a long-lived IDE context accumulates flags; is one family per workspace the right default?
11. **Agents across organizations.** A2A 1.0 [S51] or only shared Proposals?
12. **Findings declined in part.**
    - R3-53: the title stays "Agents (AGT)", because the brief fixes the title line and the README keys on it; the rest is applied.
    - R4-01: moving `send_to_machine`, `send_print_job` and `start_print` to phase 1 is declined, because contract section 13.2 defers CAM, posts and slicing to phase 2; the Acts ship with the effects they govern.
    - R5-18: its rename of `send_to_machine` is declined in favour of contract 7.6's list; `send_to_machine` carries R5-18's meaning (delivery to a DNC queue, start at the machine).
    - R4-05: program headers, offset verification, edit capture and drip-feed DNC belong to MFG, and moving DNC to phase 1 conflicts with section 13.2.
    - R6-02 item 6: phase 1 has the three roles section 13.2 names, not two.

## Contract change requests

- **CCR-AGT-7.** Passing every check: accepted in contract v5, section 7.6.
- **CCR-AGT-8.** Rig tests as a restricted Act: accepted in contract v5, sections 2 and 7.6.
- **CCR-AGT-9.** Owners of `Budget` and `PriorityClass`: accepted in contract v5, section 5.

## Sources

- [S1] MCP Specification, latest revision (2026-07-28): https://modelcontextprotocol.io/specification/latest
- [S2] MCP 2026-07-28 changelog: https://modelcontextprotocol.io/specification/2026-07-28/changelog
- [S3] MCP 2026-07-28, Tools: https://modelcontextprotocol.io/specification/2026-07-28/server/tools.md
- [S4] MCP Tasks extension: https://modelcontextprotocol.io/extensions/tasks/overview.md
- [S5] MCP 2026-07-28, Multi Round-Trip Requests: https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr.md
- [S6] MCP 2026-07-28, Authorization: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/index.md
- [S7] MCP Security Best Practices (2026-07-28): https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices.md
- [S8] MCP Skills extension: https://modelcontextprotocol.io/extensions/skills/overview.md
- [S9] MCP Apps extension: https://modelcontextprotocol.io/extensions/apps/overview.md
- [S10] Official Rust SDK for MCP (`rmcp`): https://github.com/modelcontextprotocol/rust-sdk
- [S11] Zoo, "Announcing Zookeeper, Our Conversational CAD Agent": https://zoo.dev/blog/announcing-zookeeper
- [S12] Zoo, Zookeeper research: https://zoo.dev/research/zookeeper
- [S13] Autodesk, "Introducing the Fusion MCP": https://www.autodesk.com/products/fusion-360/blog/introducing-the-fusion-mcp-opening-fusion-to-ai-powered-workflows/
- [S14] Autodesk, "Introducing the Autodesk Fusion Data MCP Server": https://www.autodesk.com/products/fusion-360/blog/introducing-the-autodesk-fusion-data-mcp-server/
- [S15] CloudNC, "What to see at IMTS 2026": https://www.cloudnc.com/blog/what-to-see-at-imts-2026-ai-assisted-cnc-programming-and-where-to-find-cloudnc
- [S16] Wang et al., "Text2CAD-Bench" (arXiv:2605.18430): https://arxiv.org/abs/2605.18430 and https://arxiv.org/pdf/2605.18430
- [S17] Alrashedy et al., "Generating CAD Code with Vision-Language Models for 3D Designs" (CADPrompt, CADCodeVerify; arXiv:2410.05340): https://arxiv.org/abs/2410.05340
- [S18] Mallis et al., "Text-to-CAD Evaluation with CADTests" (arXiv:2605.07807): https://arxiv.org/abs/2605.07807
- [S19] Dong, Li and Wu, "MUSE" (arXiv:2605.28579): https://www.alphaxiv.org/abs/2605.28579
- [S20] Rukhovich et al., "CAD-Recode" (arXiv:2412.14042): https://arxiv.org/abs/2412.14042
- [S21] Fusion 360 Gallery Dataset license: https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md
- [S22] ABC dataset: https://deep-geometry.github.io/abc-dataset/
- [S23] Onshape Terms of Use: https://www.onshape.com/en/legal/terms-of-use
- [S24] Onshape, "FeatureScript MCP Server Enables Text Code CAD": https://www.onshape.com/en/blog/featurescript-mcp-server-enables-text-code-cad
- [S25] Beurer-Kellner et al., "Design Patterns for Securing LLM Agents against Prompt Injections" (arXiv:2506.08837): https://arxiv.org/abs/2506.08837 and https://arxiv.org/pdf/2506.08837v3
- [S26] Debenedetti et al., "Defeating Prompt Injections by Design" (CaMeL; arXiv:2503.18813): https://arxiv.org/abs/2503.18813
- [S27] Microsoft Agent Framework, "FIDES": https://devblogs.microsoft.com/agent-framework/fides/
- [S28] Meta AI, "Agents Rule of Two": https://ai.meta.com/blog/practical-ai-agent-security/
- [S29] OWASP, "LLM01:2025 Prompt Injection": https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- [S30] OWASP Top 10 for Agentic Applications for 2026 (resource page, published 9 December 2025): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ ; item list as reproduced at https://docs.modulos.ai/frameworks/owasp-top-10-agentic
- [S31] Anthropic, "Writing effective tools for agents": https://www.anthropic.com/engineering/writing-tools-for-agents
- [S32] Anthropic, "Building effective agents": https://www.anthropic.com/engineering/building-effective-agents
- [S33] Anthropic, "How we built our multi-agent research system": https://www.anthropic.com/engineering/multi-agent-research-system
- [S34] Debenedetti et al., "AgentDojo" (arXiv:2406.13352): https://arxiv.org/abs/2406.13352
- [S35] Yao et al., "τ-bench" (arXiv:2406.12045): https://arxiv.org/abs/2406.12045
- [S36] Yang et al., "Set-of-Mark Prompting" (arXiv:2310.11441): https://arxiv.org/abs/2310.11441
- [S37] Ament et al., "Unexpected Improvements to Expected Improvement for Bayesian Optimization" (arXiv:2310.20708): https://arxiv.org/abs/2310.20708
- [S38] BoTorch documentation, multi-objective optimization (v0.18.1): https://botorch.org/docs/multi_objective
- [S39] Daulton, Balandat and Bakshy, "Hypervolume Knowledge Gradient" (ICML 2023): https://proceedings.mlr.press/v202/daulton23a.html
- [S40] Hvarfner, Hellsten and Nardi, "Vanilla Bayesian Optimization Performs Great in High Dimensions" (arXiv:2402.02229): https://arxiv.org/abs/2402.02229
- [S41] pymoo algorithm list (0.6.2): https://pymoo.org/algorithms/list.html
- [S42] Digital Engineering 24/7, "Siemens Brings AI Copilot, Immersive Design to NX": https://www.digitalengineering247.com/article/siemens-brings-ai-copilot-immersive-design-to-nx
- [S43] Siemens Designcenter blog, Designcenter X NX Copilot tips (post 13115): https://blogs.sw.siemens.com/designcenter/wp-json/wp/v2/posts/13115
- [S44] Epoch AI, CadEval: https://epoch.ai/benchmarks/cad-eval
- [S45] RFC 9457, "Problem Details for HTTP APIs": https://www.rfc-editor.org/rfc/rfc9457.html
- [S46] IETF draft, "The Idempotency-Key HTTP Header Field" (draft-07, expired): https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/
- [S47] RFC 8693, "OAuth 2.0 Token Exchange": https://www.rfc-editor.org/rfc/rfc8693.html
- [S48] in-toto Attestation Framework, Statement v1: https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md
- [S49] 15 CFR 734.18, activities that are not exports (eCFR): https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734/section-734.18
- [S50] 22 CFR 120.54, activities that are not exports (eCFR): https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54
- [S51] A2A Protocol specification (version 1.0.0): https://a2a-protocol.org/latest/specification/
- [S52] 22 CFR 120.54, paragraphs (a)(5) and (b), Cornell LII: https://www.law.cornell.edu/cfr/text/22/120.54
- [S53] 22 CFR 120.56, release, Cornell LII: https://www.law.cornell.edu/cfr/text/22/120.56
- [S54] MCP 2026-07-28, Elicitation (URL mode and phishing): https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation
- [S55] MCP 2026-07-28, Authorization security considerations (localhost redirect URI risks): https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations
- [S56] GDPR Article 17, right to erasure: https://gdpr-info.eu/art-17-gdpr/
- [S57] Works Constitution Act (Betriebsverfassungsgesetz), English translation, section 87: https://www.gesetze-im-internet.de/englisch_betrvg/englisch_betrvg.html
- [S58] RFC 9449, "OAuth 2.0 Demonstrating Proof of Possession (DPoP)": https://www.rfc-editor.org/rfc/rfc9449.html
- [S59] OpenID Connect Core 1.0, section 9, client authentication (`private_key_jwt`): https://openid.net/specs/openid-connect-core-1_0.html
- [S60] W3C, "Web Authentication: An API for accessing Public Key Credentials, Level 3" (Recommendation, 25 August 2026): https://www.w3.org/TR/webauthn-3/
- [S61] Mesa documentation, LLVMpipe: https://docs.mesa3d.org/drivers/llvmpipe.html
- [S62] Ebelin et al., "ꟻLIP: A Difference Evaluator for Alternating Images" (High Performance Graphics 2020): https://research.nvidia.com/labs/rtr/publication/andersson2020flip/
