# Agents (AGT)

Agents use the same typed `api` as people: one method catalog, served over MCP 2026-07-28 and native Rust, Python and TypeScript SDKs. Agents edit only branches and deliver Proposals that build, pass every Check and carry signed provenance. The server, not the model, enforces safety: untrusted content cannot trigger consequential actions, and every irreversible real-world action needs a human to approve the exact action.

## Scope, invariants and terms

This tab specifies the `api` method catalog and its transports, observation interfaces, built-in roles, swarm orchestration and the Proposal flow. It also covers safety, model independence, benchmarking, training data and agent-facing documentation. Kiln, `repo`, Anvil, Flux and the platform layer own the machinery underneath; this tab states what it requires from them.

Invariants:

1. **Parity of capability.** Every API method is available to people and agents alike, and the UI, CLI and CI call the same methods. Authority differs on purpose: only accountable humans approve irreversible effects, protected merges and policy changes.
2. **Branch confinement.** Agents write only to unprotected branches, normally ones they own; a human may invite an agent onto a shared working branch. Protected branches change only through Proposals.
3. **Proposals are the unit of agent work.** A Proposal enters review only after it builds, passes every Check and carries server-generated snapshots. A Check that should not apply is changed or waived in source, which is itself a reviewed, high-risk change.
4. **Enforcement lives in the server.** `api` checks permissions, budgets, labels and approvals on every call, whatever model or host drives the agent.
5. **No correctness depends on a model.** Every agent output becomes Ingot source or a typed record that deterministic Checks verify.
6. **Every claim has an oracle.** Role exit criteria are Checks, and benchmark graders live in `oracles/agents/`, which agents can read but not write.

This tab uses plain names for the concepts it adds. Each relates to the core types as follows.

| Term | Meaning | Relation to core types |
| --- | --- | --- |
| API method | One typed request and response in the `api` catalog, such as `edit.apply` | Not an Operation. A method may demand many Ops through Kiln. |
| Session | A server-minted handle binding a principal, a branch, a grant, a budget and labels | Required by every method that changes state or spends budget |
| Evaluation | One request to Kiln to demand Op results: a build, checks, a simulation, CAM, cost or an exploration | The Evaluation names the request; Ops are the cached nodes it demands |
| Role | An Ingot record plus skill files giving an agent's purpose, scopes, exit criteria and outputs | Published as a package |
| Work item | One node of a swarm plan, executed as a child Proposal | Stored on the parent Proposal |
| Approval | Human consent, with step-up authentication, bound to one action digest | Required by `act.commit` |
| Labels | The integrity label and data class attached to every value the API returns; a session that has read untrusted text is tainted | Propagate to derived artifacts in CAS |
| Plan | A validated set of work items for a swarm | Stored on a parent Proposal |
| Act | An effect outside the design repository, such as a release or an order, executed in two phases with human approval | Recorded in the audit log, not as a `repo` change |
| Risk class | R0 to R4, computed by the server from a Proposal's semantic diff and labels | Decides review and auto-merge rules |

The brief calls the catalog an "operation catalog". This tab says "API method" because the glossary reserves Operation for Anvil and Flux primitives. In this tab, "Evaluation" always means a Kiln request, so the brief's "evaluation" of agents is called benchmarking here.

## The agent API

### One catalog, several transports

**Decision D-AGT-1:** The `api` method catalog is the only programmatic surface of Crucible; MCP tools, SDK methods, UI commands and CLI subcommands map one-to-one onto API methods. *Why:* agents are first-class users, and a second surface would drift from the first; Principle 1 forbids privileged paths. *Rejected:* a separate agent API (drifts and doubles testing); a code-only surface that runs scripts (loses typed inspection, evaluation and review).

The layering is strict:

- `core/api` holds method types, dispatch, policy enforcement, labels, budgets, the idempotency store and the audit log. It contains no transport code.
- The desktop app, the web app and the CLI link `core/api` in process.
- `apps/mcp` serves the catalog over MCP on stdio and Streamable HTTP. It builds on the official Rust SDK, `rmcp`, which implements 2026-07-28 and stays compatible with 2025-11-25 [S10].
- The Rust SDK re-exports `core/api` types with an HTTP client. The Python and TypeScript SDKs are generated from the same JSON Schemas.
- `apps/crew`, the hosted crew runtime, reaches Crucible only through the public SDK. It has no other access path.

### MCP profile

MCP 2026-07-28 is the current revision [S1]. It removes protocol-level sessions and the initialization handshake, so every request carries its protocol version and client capabilities in `_meta` [S2]. Servers that need state across calls mint explicit handles, passed as tool arguments [S2].

The revision also replaces server-initiated requests with Multi Round-Trip Requests (MRTR), moves Tasks into an official extension, and deprecates Roots, Sampling and Logging [S2].

**Decision D-AGT-2:** Crucible targets MCP 2026-07-28 with the Tasks and Skills extensions. It serves 2025-11-25 clients for at least twelve months after phase 1 and uses no deprecated MCP capability. *Why:* stateless requests let team servers scale horizontally without sticky sessions, and the deprecated capabilities have a removal window of at least twelve months [S2]. *Rejected:* a custom agent protocol (no host ecosystem); building on 2025-11-25 (needs session affinity and is the superseded revision).

| MCP element | Crucible use |
| --- | --- |
| `server/discover` | Advertises protocol versions, the `io.modelcontextprotocol/tasks` and `io.modelcontextprotocol/skills` extensions and the `api` catalog version [S2][S4][S8] |
| `tools/list` | One tool per API method the caller's grant allows. The spec permits the list to vary by authorization, not by connection [S3]. Order is deterministic, which the spec recommends for prompt caching [S3]. |
| `tools/call` | Invokes a method. Every tool declares `outputSchema` and returns `structuredContent` plus a short text summary [S3]. Domain failures are tool execution errors with `isError: true` [S3]. |
| Resources | `crucible://` URIs for revision-addressed source, scene graphs, renders, Fields, CAS blobs, docs and error entries. Revision-addressed results never change, so they carry a long `ttlMs` with `cacheScope: "private"` [S2]. |
| `subscriptions/listen` | Resource subscriptions on branch-head, Proposal and Evaluation resources, plus `toolsListChanged` when a grant changes, on one long-lived stream [S2] |
| Tasks extension | Long Evaluations return `resultType: "task"`; clients poll `tasks/get`, answer `tasks/update` and stop work with `tasks/cancel` [S4] |
| MRTR and URL-mode elicitation | Act approvals. The server returns an `InputRequiredResult` carrying a URL-mode elicitation; the client retries with `inputResponses` and the echoed `requestState` [S5]. Step-up authentication uses OAuth `insufficient_scope` challenges instead [S6]. |
| Skills extension | Role instructions as `skill://crucible/<role>/SKILL.md` with SHA-256 file manifests [S8] |
| Apps extension | The proposal review viewer as a `ui://` resource rendered in a sandboxed iframe (phase 2) [S9] |
| Prompts | Role entry prompts, for hosts that lack the Skills extension |
| `_meta` | W3C `traceparent` for OpenTelemetry [S2] and a Crucible-namespaced catalog version key |
| HTTP headers | Gateways rate-limit on the required `Mcp-Method` and `Mcp-Name` headers; `x-mcp-header` mirrors the `repo` argument into `Mcp-Param-Repo` for shard routing [S2][S3] |
| Not used | Sampling, Roots and Logging (deprecated), HTTP+SSE (deprecated) [S2] |

Because `requestState` passes through the client, the spec requires integrity protection whenever it affects authorization [S5]. It recommends binding the state to the principal, a short expiry and a digest of the original request [S5]. Crucible seals `requestState` with AEAD and binds all three, with a 15-minute expiry by default.

The method id `edit.apply` becomes the MCP tool `edit_apply`. MCP allows dots in tool names [S3], but some model APIs restrict tool names to letters, digits, underscore and hyphen [unverified for every provider].

Tool annotations mark read-only, destructive and idempotent methods, using the hint fields that earlier MCP revisions define [unverified for 2026-07-28]. Clients must treat annotations as untrusted unless the server is trusted [S3], so the hosted crew trusts them only from a server identity it has pinned.

### Sessions, identity and delegation

A principal is a person (`user:<id>`), an agent instance (`agent:<org>/<role>/<instance>`) or a service (`service:<name>`). An agent always acts for a human.

Crucible records the delegation chain with the semantics of the OAuth Token Exchange `act` claim, in which the outermost actor is current and nested actors are prior [S47]. A planner that spawns a worker therefore yields the chain human → planner → worker.

Remote transports use OAuth 2.1 as MCP specifies: protected resource metadata (RFC 9728), resource indicators (RFC 8707), audience-bound tokens, and step-up through `insufficient_scope` challenges [S6]. Clients register with Client ID Metadata Documents, since Dynamic Client Registration is deprecated [S2][S6].

The local stdio server takes credentials from the environment, as the spec directs [S6], meaning the signed-in user's credential in the OS keychain. The hosted crew mints one downscoped token per worker by token exchange [S47].

**Decision D-AGT-3:** A Session is an opaque 128-bit random handle that the server binds to the authenticated principal and token issuer. It expires after 24 hours idle or 7 days total by default. Atomicity is per change, isolation is per branch, and Crucible has no long-lived transaction object. *Why:* MCP 2026-07-28 has no protocol sessions and recommends explicit handles [S3]; the MCP security guidance says possession of a handle must never count as authentication [S7]; cheap branches already isolate work. *Rejected:* protocol-level sessions (removed from MCP); multi-call transactions with locks (contention, leaked locks, a second concept beside branches).

```rust
pub struct SessionOpen {
    pub repo: RepoId,
    pub branch: BranchSpec,              // Existing(BranchName) | Fork { name, from: RevisionRef }
    pub role: Option<RoleRef>,           // e.g. "std::agents::detail_designer@1"
    pub scopes: Vec<Scope>,              // requested; the effective grant is an intersection
    pub write_set: Option<WriteSet>,     // path and feature-path globs this session may edit
    pub budget: Budget,
    pub purpose: String,                 // shown in the audit log and in review
    pub endpoint: Option<EndpointId>,    // hosted crew: the attested model endpoint
    pub work_item: Option<WorkItemId>,   // set when a planner spawns the session
}

pub struct SessionOpened {
    pub session: SessionHandle,
    pub branch: BranchName,
    pub head: RevisionId,
    pub grant: Grant,                    // effective scopes, write set, clearance, expiry
    pub budget: BudgetAccount,
    pub labels: SessionLabels,           // integrity taint and data-class clearance
}
```

The effective grant is the intersection of the delegating human's permissions, the role's scopes, the repository policy and the request. Clearance is the minimum of the human's clearance, the model endpoint's clearance and the repository policy. A session never holds more authority than the human it acts for.

A person may opt in, through `session.presence`, to share presence with an agent session: the current selection as `EntityId`s and the camera. This gives agents the selection awareness that Zoo's Zookeeper offers, where selecting faces and prompting "round the edges" targets that geometry [S11].

### Changes, branches and concurrency

`edit.apply` applies a list of edits atomically and records one `repo` change. Structured edits exist because they are hard to get wrong. Every edit lowers to an Ingot source patch, and the response returns that patch.

```rust
pub struct ApplyEdits {
    pub session: SessionHandle,
    pub base: RevisionId,                // must be exact; stale bases are handled by on_stale
    pub edits: Vec<Edit>,
    pub on_stale: OnStale,               // Fail | RebaseIfDisjoint (default)
    pub message: String,
    pub dry_run: bool,                   // diagnostics and diff without recording a change
    pub allow_errors: bool,              // own unprotected branches only; default false
}

pub enum Edit {
    Patch { path: SourcePath, range: TextRange, expected: Sha256, replacement: String },
    SetParameter { target: FeaturePath, param: Ident, value: IngotExpr },  // "4mm ± 0.1mm"
    InsertFeature { after: FeaturePath, binding: Ident, call: IngotExpr },
    RemoveFeature { target: FeaturePath, cascade: Cascade },
    RenameSymbol { symbol: SymbolPath, to: Ident },
    AddCheck { target: FeaturePath, predicate: IngotExpr, severity: Severity, trace: Option<Trace> },
    SetMaterial { part: FeaturePath, material: MaterialRef },
    AddDependency { package: PackageName, version: VersionReq },
    CreateFile { path: SourcePath, contents: String },
    DeleteFile { path: SourcePath, expected: Sha256 },
}

pub struct EditsApplied {
    pub revision: RevisionId,
    pub rebased: Option<Rebase>,         // present whenever the base moved
    pub patch: Vec<SourcePatch>,         // the Ingot the edits became, formatted
    pub diagnostics: Vec<Diagnostic>,    // parse, type and unit errors from the compiler
    pub diff: SemanticDiffSummary,
    pub usage: Usage,
}
```

**Decision D-AGT-4:** Structured edits are a convenience layer that lowers to Ingot source patches; the formatter normalizes touched regions, and the response returns the patch. *Why:* one model, three editors; reviewers and agents read the same Ingot whatever produced it. *Rejected:* edits on geometry or on an opaque feature tree (nothing exists only outside Ingot).

An edit that introduces compile errors is rejected with `edit.introduces_errors`, unless `allow_errors` is set on the agent's own unprotected branch. A `Patch` carries the SHA-256 of the text it replaces, so a patch computed against stale text fails with `edit.patch_mismatch` instead of corrupting the file. Edits outside the session's write set fail with `edit.write_set_violation`.

**Decision D-AGT-5:** Concurrency control is optimistic: every mutating call names its base revision. On a stale base the server rebases only when `repo`'s semantic merge reports no overlap in touched files, features, parameters or entities, and it reports the rebase in the response. *Why:* explicit over magic; agents need to know their view was stale. *Rejected:* pessimistic locks (deadlocks, abandoned locks from crashed agents); silent rebase (hides semantic interference).

Transactions on branches have three scopes, and all are atomic:

1. One `edit.apply` call is one change on the session's branch: all of its edits are recorded, or none are.
2. A Proposal merge applies the whole branch to its target as one change.
3. A swarm's parent Proposal applies every child's work to the target in one merge.

When a person and an agent share a branch, the agent's change enters the live-collaboration CRDT as one atomic batch. By default agents work on their own branches, where the only writer is the agent. To roll back, an agent resets its own unprotected branch to an earlier revision with `edit.reset_branch`.

### Idempotency and retries

MCP 2026-07-28 removed stream resumability: a broken response stream loses the in-flight request, and the client must re-issue it with a new request id [S2]. Retries are therefore routine, and a retried mutation must not apply twice.

**Decision D-AGT-6:** Every method that changes state or spends budget requires an idempotency key, a client-generated 128-bit random value. The server stores (principal, method, key) with a SHA-256 fingerprint of the canonical arguments and the response for 24 hours. *Why:* exactly-once effects under routine retries. *Rejected:* best-effort deduplication by argument hash (merges legitimately repeated calls); relying on transport resumability (removed from MCP).

The design is modeled on the IETF Idempotency-Key draft, which expired at draft-07 without becoming an RFC [S46]. Crucible defines its own semantics and does not depend on the draft.

| Situation | Behavior |
| --- | --- |
| Same key, same fingerprint, completed | Returns the stored response, marked `replayed: true` in `_meta` |
| Same key, same fingerprint, still running | `request.in_flight` with `retry_after_ms` |
| Same key, different fingerprint | `request.idempotency_mismatch`, naming the original method and time |
| Key older than 24 hours | Treated as new; the response says the key had expired |
| Read-only method | Key ignored |

Over MCP the key is the `idempotency_key` argument of every such tool; over HTTP it is also mirrored into a header for gateways. The SDKs generate keys and retry transport failures with the same key, using capped exponential backoff with jitter.

### Evaluations and streaming results

Builds, checks, simulations, CAM, costing and explorations run as Evaluations on Kiln, which streams coarse results first [contract §7].

An Evaluation moves through `queued`, `running`, `input_required`, `completed`, `failed` and `cancelled`. Both `queued` and `running` map to the MCP task state `working`, and the rest map one-to-one [S4].

```rust
pub enum Frame {
    Progress { fraction: f32, stage: String },
    Diagnostics(Vec<Diagnostic>),
    BodyReady { node: NodeId, fidelity: Fidelity, body: CasRef },
    CheckResult(CheckOutcome),          // pass | fail | error | skipped, value, margin, oracle source
    FieldReady { field: FieldRef, fidelity: Fidelity, error_estimate: Option<ErrorEstimate>,
                 validity: ValidityStatus },
    ParetoUpdate(ParetoFront),          // explorations only
    Usage(Usage),
    Final(EvaluationReport),
}
```

When the client declared the Tasks extension, a long Evaluation returns a task handle. The client then polls `tasks/get` or receives `notifications/tasks` through `subscriptions/listen` [S4]. A short Evaluation completes within the call, and its progress notifications travel on that request's response stream [S2].

Frames are read from the resource `crucible://evaluation/{id}/frames?after={seq}` or with `evaluate.get`. When the client lacks the extension, the method waits up to `wait_ms` and then returns the Evaluation id for polling. The spec forbids returning a task to a client that did not declare support [S4].

The SDKs expose Evaluations as asynchronous streams: `Stream<Item = Result<Frame, ApiError>>` in Rust, async iterators in Python and `AsyncIterable` in TypeScript. Cancellation is cooperative. Kiln stops at the next Op boundary, partial results stay in CAS, and the final frame states what completed.

### Rate, cost and size limits

```rust
pub struct Budget {
    pub money: Option<Money>,            // priced by the deployment's price table
    pub core_seconds: Option<u64>,
    pub gpu_seconds: Option<u64>,
    pub model_tokens: Option<u64>,       // hosted crew only; external hosts are not metered
    pub wall_clock: Option<Duration>,
    pub max_evaluations: Option<u32>,
}

pub struct Usage {
    pub core_seconds: u64, pub gpu_seconds: u64, pub memory_gb_seconds: u64,
    pub cas_bytes_written: u64, pub model_input_tokens: u64, pub model_output_tokens: u64,
    pub cost: Money,
}
```

Budgets form a hierarchy: organization, project, Proposal tree, work item, session. A child's budget is carved from its parent's and returns to it unused.

Every Evaluation passes admission control: Kiln returns a cost estimate, `api` reserves it, and `budget.exceeded` comes back before any work starts if the reservation fails. The fix lists cheaper options, such as lower fidelity or a smaller batch.

Metering charges actual usage as Ops finish and releases the remainder of the reservation. At 80% of a cap the session receives a warning frame. At the cap, running Evaluations are cancelled and keep their partial results.

Rate limits are per principal and enforced at the gateway. Over HTTP they return 429 with `Retry-After`; over MCP they return `limit.rate` with `retry_after_ms`. Defaults, configurable by policy:

| Method class | Default sustained rate | Burst |
| --- | --- | --- |
| Read, `inspect.*` except render | 50 per second | 200 |
| `inspect.render`, `inspect.section` | 4 concurrent | — |
| `edit.*` | 10 per second | 30 |
| Starting Evaluations | 5 per second; concurrency limited by budget | 20 |
| `propose.*` | 1 per second | 10 |
| `act.prepare` | 10 per hour | — |

Responses default to concise detail. Callers ask for `detail: "full"` when they need more, following the finding that concise responses use about a third of the tokens [S31]. Lists paginate with opaque cursors in deterministic order.

Any result above 20,000 tokens (estimated as bytes divided by four) is truncated with a cursor and a resource link to the full content. Claude Code's 25,000-token default tool-response limit [S31] motivated that cap.

### Errors as guidance

```rust
pub struct ApiError {
    pub code: ErrorCode,                 // stable, e.g. "edit.stale_base"
    pub r#type: Uri,                     // crucible://errors/edit.stale_base (the catalog entry)
    pub title: String,                   // constant per code
    pub detail: String,                  // this occurrence, in plain words
    pub status: u16,                     // HTTP-equivalent status
    pub instance: Uri,                   // crucible://audit/{seq}: this occurrence's audit record
    pub retry: Retry,                    // Never | After(ms) | AfterChange
    pub fixes: Vec<SuggestedFix>,        // ordered, most likely first
    pub context: serde_json::Value,      // code-specific payload; schema in the catalog
}

pub enum SuggestedFix {
    ApplyEdits { edits: Vec<Edit>, explanation: String },   // machine-applicable
    Call { method: MethodId, args: serde_json::Value, explanation: String },
    Read { uri: ResourceUri, why: String },
    AskHuman { question: String },
}
```

**Decision D-AGT-7:** Every failure is an `ApiError` shaped like RFC 9457 Problem Details (`type`, `title`, `status`, `detail`, `instance` plus extension members) with typed context and ordered suggested fixes, many machine-applicable. Domain failures are MCP tool execution errors, not JSON-RPC protocol errors. *Why:* RFC 9457 is the standard machine-readable error format [S45]; MCP advises giving tool execution errors to the model so it can self-correct [S3]. *Rejected:* free-text errors (agents cannot act on them reliably); JSON-RPC errors for domain failures (the spec expects models to recover poorly from them [S3]).

Over HTTP the SDKs carry the same object as `application/problem+json` [S45]. Compiler diagnostics and `ResolveError`s arrive inside `context` with their own fixes. A `ResolveError` fix may be an edit that pins one of the candidate entities.

Error text never embeds external strings. It refers to them by `ExternalText` handle, so an error message cannot carry an injection.

| Family | Representative codes | Typical fix |
| --- | --- | --- |
| `auth` | `scope_denied`, `step_up_required`, `token_audience` | Request scope by step-up; `AskHuman` |
| `session` | `expired`, `unknown`, `branch_protected` | Open a new session; fork a branch |
| `edit` | `stale_base`, `patch_mismatch`, `introduces_errors`, `write_set_violation`, `protected_path` | Re-read and retry; apply the compiler's fix; ask the planner to widen the write set |
| `query` | `resolve_failed`, `no_robust_candidate` | Pin a candidate; use `inspect.suggest_query` |
| `build`, `flux`, `mfg` | `failed`, `study_invalid`, `outside_validity`, `setup_invalid` | Edits from diagnostics; refine the mesh; lower the load into the envelope |
| `budget`, `limit` | `exceeded`, `rate` | Lower fidelity; wait `retry_after_ms` |
| `propose` | `preconditions_failed`, `policy_unsatisfied`, `self_review_forbidden` | The failing checks and missing approvals, listed |
| `act` | `approval_pending`, `approval_expired`, `plan_changed`, `recipient_unverified`, `class_not_exportable` | Open the approval URL; prepare again |
| `label` | `tainted_session`, `class_exceeds_clearance` | Start a clean session; use a cleared endpoint |
| `request` | `idempotency_mismatch`, `in_flight` | Use a new key; wait |

### Method catalog

The catalog has 50 methods in eight groups. The contract names six groups; Session and Act are new (see Contract change requests).

Each method has a stable id and a version. Breaking changes create a new version, such as `edit.apply@2`, and the old version is served for at least twelve months, mirroring MCP's minimum deprecation window [S2]. Methods marked † change state or spend budget, so they require an idempotency key and, except `session.open`, a session. Every † request carries both; the request columns show `session` only where it clarifies the call.

**Session**

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `session.open` † | `SessionOpen` → `SessionOpened` | `auth.scope_denied`, `session.branch_protected`, `budget.unavailable`, `label.endpoint_not_cleared` | 0 |
| `session.status` | `{session}` → head, grant, labels, usage, budget left, open Evaluations, shared presence | `session.expired`, `session.unknown` | 0 |
| `session.close` † | `{session, cancel_running}` → final usage, budget returned | `session.unknown` | 0 |
| `session.presence` † | `{session, share: Selection, Camera, Both or Off}` → acknowledgment; callable only by the delegating human | `auth.not_delegator` | 1 |

**Read** (accept any `RevisionRef`: a revision, `branch@head` or a tag)

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `read.tree` | `{rev, path?, cursor?}` → entries with path, kind, size, hash, labels | `read.not_found` | 0 |
| `read.source` | `{rev, path, range?, reveal_external?}` → text, hash, labels; `external(...)` literals elided to handles unless `reveal_external`, which taints the session | `read.not_found`, `label.class_exceeds_clearance` | 0 |
| `read.outline` | `{rev, path? or feature?}` → feature tree: call, parameters, Checks, spans | `build.parse_failed` (partial outline) | 0 |
| `read.history` | `{branch, since?, cursor?, limit ≤ 100}` → changes with provenance | `read.not_found` | 0 |
| `read.branches` | `{repo, filter?}` → name, head, protection, owner | — | 0 |
| `read.symbols` | `{rev, query, kinds?}` → path, kind, signature, doc URI | — | 1 |
| `read.docs` | `{by: Symbol, Query, ErrorCode or Uri; include_examples}` → `DocEntry`s pinned to the lockfile | `docs.not_found` with nearest matches | 0 (errors), 1 (std) |
| `read.external_text` | `{handle}` → text and origin; taints the session | `read.unknown_handle` | 0 |
| `read.catalog` | `{query?, filters, cursor?}` → catalog part summaries from the local mirror | `catalog.filter_invalid` | 1 |
| `read.audit` | `{filter, cursor?}` → `AuditRecord`s; needs `audit:read` | `auth.scope_denied` | 1 |

**Inspect** (all results carry labels; geometric values carry `ErrorBound`s)

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `inspect.scene` | `{rev, root?, depth?, include?, selection?}` → `SceneGraph` | `build.failed` (partial graph and diagnostics), `inspect.too_large` (cursor) | 1 |
| `inspect.entity` | `{rev, entity}` → `EntityInfo`: kind, surface type, size, adjacency, provenance chain | `inspect.entity_gone` (with `HistoryRecord`s) | 1 |
| `inspect.query` | `{rev, query: IngotExpr}` → entities, or a `ResolveError` | `query.resolve_failed` (candidates, fixes) | 1 |
| `inspect.suggest_query` | `{rev, entities, perturbations = 16}` → robust `Query` candidates with scores | `query.no_robust_candidate` | 1 |
| `inspect.measure` | `{rev, kind, targets}` → `Quantity`, `ErrorBound`, witness points | `inspect.kind_unsupported` | 1 |
| `inspect.render` | `RenderRequest` → `Rendered` | `render.too_many_marks`, `render.gpu_unavailable` (CPU fallback, reported) | 1 |
| `inspect.section` | `{rev, plane, targets, field?}` → curves, SVG, legend | `inspect.empty_section` | 1 |
| `inspect.field` | `{rev, field, sample: Points, Region, Stats or Extrema}` → values, interpolation error, validity | `field.out_of_domain` | 1 |
| `inspect.describe` | `{rev, target, detail, audience}` → text and `DescriptionFacts` | `build.failed` (describes what built) | 0 |

`inspect.measure` kinds are distance, angle, clearance, wall thickness, mass properties and interference.

**Edit** (exact base revision required)

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `edit.apply` † | `ApplyEdits` → `EditsApplied` | `edit.stale_base`, `edit.patch_mismatch`, `edit.introduces_errors`, `edit.write_set_violation`, `edit.protected_path` | 0 |
| `edit.revert` † | `{session, base, changes}` → `EditsApplied` (the revert is a forward change) | `edit.revert_conflict` | 0 |
| `edit.create_branch` † | `{session, name, from}` → branch and head, owned by the session's principal | `edit.branch_exists`, `edit.name_reserved` | 0 |
| `edit.reset_branch` † | `{session, to}` → head; own unprotected branches only | `edit.branch_protected`, `edit.not_owner` | 0 |

**Evaluate** (each returns an Evaluation)

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `evaluate.build` † | `{rev, targets?, fidelity: Coarse or Exact, max_cost?, estimate_only?}` → `BuildReport` | `budget.exceeded`, `build.failed` | 0 |
| `evaluate.checks` † | `{rev, select?, fidelity?}` → `CheckReport` | as above | 0 |
| `evaluate.simulate` † | `{rev, study, fidelity: Interactive or SignOff}` → `SimulationReport`: Fields, error estimates, validity flags | `flux.study_invalid`; `flux.outside_validity` keeps and flags the result | 1 |
| `evaluate.manufacture` † | `{rev, setup}` → `ManufactureReport`: toolpaths, collisions, removal simulation, cycle time | `mfg.setup_invalid` | 2 |
| `evaluate.cost` † | `{rev, quantity, process?, region?}` → `CostReport`: lines, totals with intervals, price sources | `cost.unpriced_lines` (partial report) | 1 |
| `evaluate.ci` † | `{rev}` → `CiReport`, identical to the Proposal CI run | — | 1 |
| `evaluate.explore` † | `ExploreRequest` → Pareto updates as frames | `explore.space_invalid`, `explore.no_feasible_point` | 1 |
| `evaluate.materialize` † | `{session, exploration, variant}` → `EditsApplied` | `explore.variant_unknown` | 1 |
| `evaluate.get` | `{evaluation, after_frame?, wait_ms ≤ 25000}` → status, frames, result | `evaluation.unknown` | 0 |
| `evaluate.cancel` † | `{evaluation}` → status | — | 0 |

**Compare**

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `compare.diff` | `{from, to, levels, render?}` → `SemanticDiff`, with an optional overlay render | `compare.unrelated_revisions` (diff computed and flagged) | 1 |

The diff levels are source, features, parameters, checks, geometry, metrics, BOM and policy.

**Propose**

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `propose.create` † | `{session, title, rationale, target, parent?, draft?}` → `Proposal` | `propose.preconditions_failed`, `propose.target_not_allowed` | 1 |
| `propose.update` † | `{proposal, rationale?, head?, ready?}` → `Proposal` | `propose.closed` | 1 |
| `propose.get` | `{proposal}` → `Proposal` | — | 1 |
| `propose.list` | `{repo, filter, cursor?}` → Proposal summaries | — | 1 |
| `propose.review` † | `{proposal, verdict, findings, report?}` → `Review` | `propose.self_review_forbidden` | 1 |
| `propose.comment` † | `{proposal, anchor, body, reply_to?}` → `Comment` | — | 1 |
| `propose.merge` † | `{proposal, expected_head}` → merged revision | `propose.policy_unsatisfied` (lists missing conditions), `propose.conflict` | 1 |
| `propose.withdraw` † | `{proposal, reason}` → `Proposal` | — | 1 |
| `propose.plan` † | `{proposal, plan}` → validated plan and work-item states | `plan.invalid` (cycles, overlapping write sets, missing acceptance Checks) | 2 |

The review verdicts are approve, request changes and comment.

**Act** (effects outside the design repository)

| Method | Request → response | Typed failures | Phase |
| --- | --- | --- | --- |
| `act.prepare` † | `{session, action}` → `ActionPlan`: digest, deterministic summary, effects, reversibility, cost, recipients, data classes | `act.recipient_unverified`, `act.class_not_exportable` | 1 (release), 2 (send, order, publish, share) |
| `act.commit` † | `{plan_digest}` → input required, with a URL elicitation, until approved; then `ActionReceipt` | `act.approval_expired`, `act.plan_changed`, `act.denied` | 1 |
| `act.status` | `{plan_digest}` → state, approvals, receipt | — | 1 |

### Report types

The main response types of the catalog, abridged:

```rust
pub struct CheckOutcome {
    pub check: CheckRef,                 // feature path and predicate source span
    pub status: CheckStatus,             // Pass | Fail | Error | Skipped
    pub severity: Severity,
    pub value: Option<Quantity>,         // e.g. peak stress, with its ErrorBound
    pub limit: Option<Quantity>,
    pub margin: Option<f64>,             // (limit - value) / limit, signed
    pub fidelity: Option<Fidelity>,
    pub validity: ValidityStatus,        // Inside | Outside(envelope violation) | NotApplicable
    pub oracle: OracleSource,            // declared in source, or a protected oracle path
}

pub struct BuildReport { pub revision: RevisionId, pub targets: Vec<TargetOutcome>,
    pub diagnostics: Vec<Diagnostic>, pub bodies: Vec<(NodeId, CasRef)>, pub usage: Usage }
pub struct CheckReport { pub revision: RevisionId, pub outcomes: Vec<CheckOutcome>, pub usage: Usage }
pub struct SimulationReport { pub study: StudyRef, pub fields: Vec<FieldRef>,
    pub error_estimates: Vec<ErrorEstimate>, pub validity: Vec<ValidityFlag>,
    pub convergence: Option<ConvergenceTable>, pub checks: Vec<CheckOutcome>, pub usage: Usage }
pub struct CostReport { pub quantity: u32, pub lines: Vec<CostLine>, // source and date per price
    pub total: Interval<Money>, pub unpriced: Vec<BomLineRef>, pub usage: Usage }

pub struct SemanticDiff {
    pub from: RevisionId, pub to: RevisionId,
    pub source: Vec<SourcePatch>, pub features: Vec<FeatureChange>,
    pub checks: Vec<CheckChange>,        // added, removed, loosened, tightened, newly failing
    pub geometry: Option<GeometryDelta>, // volume added and removed, Hausdorff deviation, ErrorBound
    pub metrics: Vec<MetricDelta>, pub bom: Vec<BomChange>,
    pub policy_sensitive: bool,
}

pub struct Review { pub reviewer: Principal, pub verdict: Verdict, pub findings: Vec<Finding>,
    pub report: Option<CasRef>, pub at_head: RevisionId }
pub struct Finding { pub severity: Severity, pub anchor: Anchor, // EntityId, feature path or span
    pub rule: Option<String>, pub message: String, pub fix: Option<SuggestedFix>,
    pub reproduction: Option<CheckRef> } // a Check that fails on the reviewed head

pub struct ActionReceipt { pub plan_digest: Sha256, pub approvals: Vec<Approval>,
    pub executed_at: Timestamp, pub external_ref: Option<String>, pub effects: Vec<EffectResult> }
pub struct DocEntry { pub uri: ResourceUri, pub version: Version, pub signature: Option<String>,
    pub body: String, pub examples: Vec<ExampleRef>, pub errors: Vec<ErrorCode> }
pub struct AuditRecord { pub seq: u64, pub prev: Sha256, pub principal: Principal,
    pub delegation: Vec<Principal>, pub session: Option<SessionId>, pub method: MethodId,
    pub args_digest: Sha256, pub status: u16, pub labels: Labels, pub cost: Money,
    pub client: ClientInfo, pub trace: TraceId, pub at: Timestamp }
```

### Native SDKs

Rust types in `core/api` are the single source of truth. A build step emits JSON Schema 2020-12, which MCP now accepts in full for `inputSchema` and `outputSchema` [S2].

The MCP tool definitions and the generated Python and TypeScript SDKs come from those schemas. Generated types validate at runtime, and the SDK version equals the catalog version.

```python
from crucible import Client, Edit

c = Client.connect("https://crucible.example.com/mcp")   # or Client.local() for the desktop
s = c.session_open(repo="acme/bracket", fork=("agents/widen", "main"),
                   purpose="Widen the bracket to 70 mm", budget={"money": "5 USD"})
r = s.edit_apply(base=s.head, message="Widen to 70 mm",
                 edits=[Edit.set_parameter("bracket", "width", "70mm")])
async for frame in s.evaluate_checks(rev=r.revision):
    print(frame)
```

Parity is tested, not assumed. Golden transcripts drive the same calls through Rust, Python, TypeScript and raw MCP, and the canonical JSON requests and responses must be byte-identical (O-AGT-2).

## Observation interfaces

Agents perceive designs through five channels: a structured scene graph, exact geometry queries, rendered views with marks and Field overlays, deterministic text descriptions, and semantic diffs. Every channel answers from the same Kiln results, and every geometric value carries its `ErrorBound`. A text-only model receives the same facts as a vision model, so no channel is required.

### Structured scene graph

`inspect.scene` returns the evaluated product as a typed tree. It is computed from Kiln results for one revision and never from UI state.

```rust
pub struct SceneGraph {
    pub revision: RevisionId,
    pub root: SceneNode,
    pub truncated: Option<Cursor>,
    pub labels: Labels,
}

pub struct SceneNode {
    pub path: InstancePath,              // "gearbox/input_shaft[1]"
    pub kind: NodeKind,                  // Assembly | Instance | Part | Body
    pub item: Option<ItemIdentity>,      // item number, name, revision (Parts only)
    pub feature: FeaturePath,            // the Ingot feature that produced this node
    pub source: SourceSpan,
    pub placement: Option<Transform>,
    pub mates: Vec<MateSummary>,
    pub material: Option<MaterialRef>,
    pub representation: Option<Representation>, // BRep | Implicit | Mesh | SubD
    pub bbox: Option<Aabb>,              // in Length; ErrorBound attached
    pub mass: Option<MassSummary>,       // mass, centroid, principal moments, ErrorBound
    pub topology: Option<TopologyCounts>,// faces, edges, vertices, shells, genus
    pub checks: CheckSummary,            // pass, fail, error counts; worst margin
    pub fields: Vec<FieldRef>,           // Fields available on this node
    pub children: Vec<SceneNode>,
}
```

The default response is token-economical: depth 2, no topology, no Fields, and identical sibling Instances collapsed into one node with a count. Callers widen it with `include` and `depth`.

Nodes link to source spans, so an agent moves from geometry to the Ingot that made it in one step. A failed build returns the partial graph with a diagnostic on each failed node, since a partial view is more useful than none.

Contract: same revision, same parameters and same catalog version give an identical graph (O-AGT-3). Phase 1.

### Geometry queries

Agents name geometry the way Ingot does, through `Query` over provenance plus geometric predicates. They never use raw indices.

- `inspect.query` evaluates an Ingot query expression, such as `part.faces(normal: +z, area > 100mm2)`, and returns entities or a typed `ResolveError` with candidates.
- `inspect.entity` returns one entity's surface or curve type, parameters, size, adjacency and provenance chain from `HistoryRecord`s.
- `inspect.measure` returns a `Quantity` with an `ErrorBound` and witness points: the closest points for a distance, the thinnest location for wall thickness.
- `inspect.suggest_query` takes entities the agent picked from a render, perturbs the design, and returns the queries that still resolve to the same entities.

**Decision D-AGT-8:** Agents select geometry only through `Query` expressions and `EntityId`s. `inspect.suggest_query` ranks candidate queries by how stably they resolve under 16 seeded parameter perturbations within declared ranges (default ±10%). *Why:* an agent's edits must survive rebuilds and later edits as well as a person's do; the perturbation test makes robustness measurable. *Rejected:* letting agents write indices or screen coordinates into source (breaks on the next topology change); trusting the first query that resolves today.

A suggested query reports its stability score: the fraction of perturbed rebuilds that resolve to the corresponding entities. Agents must pass queries with a score of 1.0 unless they state a reason in the Proposal rationale. The DFM reviewer flags low-scoring queries.

### Rendered views and Field overlays

```rust
pub struct RenderRequest {
    pub rev: RevisionRef,
    pub targets: Option<Vec<InstancePath>>,
    pub views: Views,                    // Named(Iso | Front | Top | Right | ...) | Grid4 | Custom(Camera)
    pub style: Style,                    // Shaded | HiddenLine | Wire | XRay | Silhouette
    pub overlay: Option<FieldOverlay>,
    pub marks: Marks,                    // None | Entities { kinds, max ≤ 64 } | Explicit(Vec<EntityId>)
    pub section: Option<Plane>,
    pub size: (u16, u16),                // default 1024 x 768; max 2048 x 2048
    pub deterministic: bool,             // default true for agents
    pub buffers: Vec<Buffer>,            // Depth | Normal | EntityId (PNG, optional)
}

pub struct FieldOverlay {
    pub field: FieldRef,
    pub range: Option<(f64, f64)>,       // fixed range, in the Field's unit; default is data min..max
    pub map: ColorMap,                   // Sequential (cividis) | Diverging | Categorical
    pub isolines: Option<u8>,
    pub mark_extrema: bool,
}

pub struct Rendered {
    pub image: CasRef,                   // PNG; also inlined as MCP image content when small
    pub marks: Vec<Mark>,                // label "7" -> EntityId, kind, area or length, normal
    pub legend: Option<Legend>,          // unit, range, ticks, color stops, validity flags
    pub extrema: Vec<Probe>,             // location, value with interpolation error
    pub camera: Camera,
    pub visible_summary: String,         // the same content in words, for text-only models
}
```

The renderer is the UIX tab's renderer running headless. Marks follow Set-of-Mark prompting: numbered labels drawn on regions, which let GPT-4V outperform a fully fine-tuned referring-expression model zero-shot on RefCOCOg [S36]. Each label maps to an `EntityId` in `marks`, so "fillet the edges marked 3 and 7" resolves exactly.

Labels are placed at the visible centroid of each entity, with leader lines when regions are small, and hidden entities are never marked. Field overlays use a perceptually uniform sequential map by default and a diverging map centered on zero for signed quantities. The legend is drawn into the image and also returned as data, with units.

A `Grid4` request returns front, top, right and isometric views in one 2×2 image. Zookeeper takes four-view snapshots to review its own changes [S11]. A single composite costs one image instead of four.

**Decision D-AGT-9:** Renders requested by agents default to the deterministic CPU reference path, and every render returns its marks, legend and extrema as structured data plus a plain-text summary. *Why:* snapshots attached to Proposals and used in benchmark grading must be reproducible; text-only models must not be second-class. *Rejected:* GPU-only renders (vary by vendor and driver); images without structured side data (vision models misread small labels and colors).

Failure behavior: a GPU-only effect such as ambient occlusion is silently omitted in deterministic mode, and the response lists what was omitted. More than 64 marks returns `render.too_many_marks` with a fix that narrows the targets. Phase 1; Field overlays in phase 1 for Flux results.

### Sections

`inspect.section` cuts the design with a plane and returns section curves as typed geometry, an SVG with hatching per material, and an optional raster with a Field overlay. Section curves carry the cut-plane `ErrorBound`.

Agents use sections for wall thickness, internal clearances and stress through a cross-section. An empty cut returns `inspect.empty_section` and the nearest offset that intersects material.

### Text descriptions

`inspect.describe` produces a description of a design, a feature, an Instance or a diff. It is generated deterministically from typed facts by templates, without any model.

```rust
pub struct Description {
    pub text: String,                    // Markdown, at the requested detail level
    pub facts: DescriptionFacts,         // every number in the text, with source and ErrorBound
    pub detail: Detail,                  // Brief (≤ 80 words) | Standard (≤ 400) | Full
}
```

Example output at the brief level:

> Part `bracket` (item 100-0042), aluminum 6061-T6. Bounding box 60.0 × 40.0 × 24.0 mm; mass 41.2 g ± 0.1 g. Features: sketch, extrude 4 mm, rib 20 mm, fillet 2 mm on 2 edges. Checks: 3 pass, 0 fail; worst margin `peak_stress` 31% (interactive fidelity, error estimate 4%).

**Decision D-AGT-10:** Canonical text descriptions are template-generated from typed facts and contain no model-generated text; models may summarize them, but the canonical form is the one stored, diffed and shown in review. *Why:* descriptions feed reviews and benchmarks, so they must be reproducible and free of hallucination; every number traces to a fact with a source. *Rejected:* model-written descriptions as canonical output (non-deterministic, unverifiable).

Templates are Ingot-side metadata: a feature's doc metadata supplies its phrasing, so a third-party package describes its features as well as std does. Templates from unverified publishers are untrusted text, so descriptions that use them carry the untrusted label.

Contract: every number in `text` appears in `facts` (O-AGT-4). Phase 0 for source-level facts, phase 1 for evaluated facts.

### Semantic diffs

`compare.diff` explains what changed between two revisions at several levels.

| Level | Content | Source |
| --- | --- | --- |
| Source | Ingot text diff, formatted | `repo` |
| Features | Features added, removed, moved; parameters changed, old → new with units | `repo` semantic merge model |
| Checks | Newly failing, newly passing, margin changes, Checks added, removed or loosened | Kiln check results |
| Geometry | Volume added and removed, maximum deviation (Hausdorff) with `ErrorBound`, faces changed by provenance | Anvil |
| Metrics | Mass, cost, peak stress, cycle time and other declared objectives, with deltas and intervals | Kiln, Flux, cost model |
| BOM | Lines added, removed, quantity changes, new catalog parts | `repo` BOM query |
| Policy | Changes to Checks, tolerances, oracle references, protected paths, lockfile | `repo` |

The geometry overlay render shows added material in one color and removed material in another, from a color-blind-safe pair, with unchanged geometry ghosted.

Any diff touching Checks, tolerances or protected paths sets `policy_sensitive: true`, which review policy uses (see the Proposal and review flow). Phase 1.

### Untrusted text inside designs

Designs contain text that came from outside: names and notes in imported STEP files, supplier datasheets, catalog descriptions, comments written by other agents, and pasted requirement documents. Read results never place such text where a model could mistake it for instructions.

Each untrusted string comes back as a typed `ExternalText` value with an origin, a length and a handle. The text itself is fetched only through `read.external_text`, which marks the session as tainted (see Safety). Planners can then reason about a design's structure without ever reading its untrusted strings.

Importers generate neutral identifiers, such as `part_017`, and keep original names as `external(...)` metadata, so foreign names never become Ingot identifiers. The renderer never draws external strings: marks are numbers, and labels come from typed data.

The same rule covers text written by people and agents. Change messages, comments, rationales and review text authored outside the reading session's delegation chain come back as `ExternalText` handles, in `read.history`, `propose.get` and every other method.

## Built-in roles: the crew

A role is a typed definition published as a package. It names a purpose, scopes, a write-set rule, a policy for external text, exit Checks, outputs, model requirements and a skill. The crew is the set of roles in the open-source `std::agents` package.

Anyone can publish a role the same way, and the hosted crew runtime and external MCP hosts load roles through the same mechanism. A role from another publisher loads only after a holder of `policy:admin` approves that package version and its manifest digest, because a skill is instructions.

```rust
pub struct Role {
    pub name: RoleName,                         // "std::agents::dfm_reviewer"
    pub version: u32,
    pub purpose: String,
    pub scopes: Vec<Scope>,
    pub write_set: WriteSetRule,                // None | FromWorkItem | Fixed(Vec<Glob>)
    pub external_text: ExternalTextPolicy,      // Never | Quarantined | Direct
    pub exit_checks: Vec<CheckRef>,             // std::agents::exit::*
    pub outputs: Vec<OutputKind>,
    pub requires: ModelRequirements,            // capabilities and independence constraints
    pub skill: SkillRef,                        // skill://crucible/<role>/SKILL.md + manifest digest
}
```

**Decision D-AGT-11:** Roles are data plus instructions in an open package, and their exit criteria are Checks in `std::agents::exit`, evaluated by CI over the Proposal through a typed `std::proposal` view. *Why:* "no privileged code" applies to agents too; exit criteria must be machine-checkable to be oracles. *Rejected:* roles hard-coded in the runtime (privileged and opaque); prose-only exit criteria (not enforceable).

Role instructions are SKILL.md files, served through the MCP Skills extension as `skill://crucible/<role>/SKILL.md`. The extension requires YAML frontmatter with `name` and `description`, plus a manifest with each file's SHA-256 digest and size [S8]. Hosts must verify digests, bind approvals to the manifest, and treat skill content as untrusted input [S8].

Crucible records the manifest digest in each change's provenance. A role skill changes only through a reviewed Proposal to `std::agents`, and the agent benchmarks gate it (see Benchmarking agents).

### Scopes

Scopes are the units of permission in grants, OAuth tokens and role definitions. Following the MCP scope-minimization guidance, there is no wildcard scope and hosts request scopes incrementally by step-up [S7].

| Scope | Grants |
| --- | --- |
| `design:read` | Read methods except `read.external_text` and `read.audit`; Inspect; Compare |
| `external:read` | `read.external_text`. Each read taints the session. |
| `design:edit` | Edit methods on the session's own branch, within its write set |
| `eval:build` | `evaluate.build`, `evaluate.checks`, `evaluate.ci` |
| `eval:simulate[:fidelity]` | `evaluate.simulate`, up to the stated fidelity |
| `eval:manufacture` | `evaluate.manufacture` |
| `eval:cost` | `evaluate.cost` |
| `eval:explore` | `evaluate.explore`, `evaluate.materialize` |
| `propose:author` | `propose.create`, `update`, `withdraw`, `comment` |
| `propose:review` | `propose.review`, except on Proposals from the reviewer's own lineage |
| `propose:merge` | `propose.merge` when the target's policy is satisfied |
| `propose:plan` | `propose.plan` and opening child sessions for work items |
| `catalog:read` | `read.catalog` |
| `act:<class>` | `act.prepare` and `act.commit` for one action class. Commit always waits for human approval. |
| `audit:read` | `read.audit` |
| `policy:admin` | Changes to protection rules, auto-merge policy, oracle paths, data classes and endpoint clearances. Humans only. |

`policy:admin` is the one scope no agent can hold, by construction. Agents may draft policy changes as Proposals, and humans merge them.

### Role catalog

| Role | Edits (write set) | Evaluates | External text | Act classes | Phase |
| --- | --- | --- | --- | --- | --- |
| Planner | None (merges children into its integration branch) | Estimates only | Never | None | 2 |
| Requirements analyst | `requirements/**` | build, checks | Quarantined | None | 1 |
| Concept designer | Own concept branches | build, simulate:interactive, explore, cost | Never | None | 1 |
| Detail designer | Work-item write set | build, checks, simulate:interactive | Never | None | 1 |
| Simulation engineer | `studies/**`, Checks on results | simulate (both fidelities), checks | Never | None | 1 |
| DFM reviewer | None (suggests edits) | checks with DFM rule packages; manufacture estimates from phase 2 | Never | None | 1 |
| CAM programmer | `mfg/cam/**` | manufacture, checks | Quarantined (tool data) | `send_to_machine` | 2 |
| Cost engineer | `cost/**` and cost-reduction branches | cost, explore | Quarantined (quotes) | `request_quote` | 2 |
| Drawing and MBD author | `docs/drawings/**`, PMI annotations | build, checks | Never | None | 2 |
| Catalog librarian | Catalog package repository | build, checks | Quarantined | `publish_package` | 2 |
| Documentation writer | `docs/**` except drawings | build (renders) | Never | None | 1 |
| Independent verifier | Own scratch and counter-proposal branches; never the reviewed branch | all | Never | None | 1 |

Every role holds `design:read` and `propose:author`. The verifier and the DFM reviewer also hold `propose:review`, and the planner holds `propose:plan` and `propose:merge` limited to its own integration branch.

"Quarantined" means the role reads external text only through a quarantined extraction step (see Safety).

### Planner

- **Purpose.** Turn a goal into a validated plan of work items, dispatch them, and assemble the parent Proposal. The planner never edits design source.
- **Methods.** Read, Inspect, `inspect.describe`, `evaluate.build` with `estimate_only`, `propose.plan`, `propose.create` for the parent (a draft until assembly), `propose.merge` into the integration branch.
- **Exit Checks.** `plan_is_acyclic`; `parallel_write_sets_disjoint`; `every_item_has_acceptance_checks`; `budgets_within_parent`; `parent_ci_green`; `verifier_approved`.
- **Outputs.** A `Plan` stored on the parent Proposal, an integration branch, and the parent Proposal with a rationale linking every requirement to the work items that address it.
- **Failure behavior.** After an item exhausts its attempts, the planner re-plans once, then escalates to the requesting human with the typed failure history.

### Requirements analyst

- **Purpose.** Turn a brief, documents and standards into typed, traceable requirements.
- **Methods.** Read, `read.external_text` through quarantine, `read.docs`, `edit.apply` on `requirements/**`, `evaluate.checks`.
- **Exit Checks.** `every_requirement_has_id_and_source`; `every_requirement_has_verification_method` (analysis, test, inspection or demonstration); `quantities_typed` (units checked by the compiler); `no_duplicate_ids`; `open_questions_listed`.
- **Outputs.** `requirements/*.ingot`: typed requirement records, each with a `require` stub where it is verifiable by analysis; a trace matrix; and a list of open questions for the human.
- **Failure behavior.** Ambiguous inputs become open questions, never guesses. A requirement the analyst cannot quantify is recorded as `unquantified` and blocks the plan until a human answers it.

```
pub requirement R_017 = Requirement {
    text: external("Bracket supports 1.2 kN at the load face with safety factor 1.5"),
    source: doc("brief-v3.pdf", page: 4),       // quoted from an external document
    verify: Verification.analysis,
    check: peak_stress(bracket, 1.2kN) < yield(alu_6061_t6) / 1.5,
}
```

### Concept designer

- **Purpose.** Propose two to five distinct concepts that satisfy the requirements at coarse fidelity, and compare them.
- **Methods.** Edit on its own concept branches, `evaluate.build` (coarse), `evaluate.simulate` (interactive), `evaluate.explore` for sizing, `evaluate.cost`, `inspect.render`.
- **Exit Checks.** `concepts_distinct` (pairwise topology or architecture difference above a threshold); `each_concept_builds`; `requirements_coverage_reported`; `comparison_table_complete`.
- **Outputs.** One branch per concept, each holding a parametric skeleton, key dimensions and coarse Checks; a comparison of mass, cost interval, key margins and risks; snapshots.
- **Failure behavior.** If a concept cannot meet a requirement at any sampled point, the designer reports it as infeasible with the exploration evidence and does not drop it silently.

### Detail designer

- **Purpose.** Turn a chosen concept or a work item into complete, robust, toleranced features.
- **Methods.** Edit within the work-item write set, `inspect.suggest_query`, `evaluate.build` (exact), `evaluate.checks`, `evaluate.simulate` (interactive).
- **Exit Checks.** `builds_exact`; `all_checks_pass`; `no_new_unrobust_queries` (stability score 1.0, or a stated reason); `edits_within_write_set`; `tolerances_on_mating_features`; `no_allow_errors_changes`.
- **Outputs.** A Proposal with Ingot features, materials, tolerances, GD&T properties, and Checks for every requirement assigned to the item.
- **Failure behavior.** A resolve or build failure the designer cannot fix within its attempts becomes a typed failure report on the work item.

### Simulation engineer

- **Purpose.** Set up studies, run them at the right fidelity, and turn their results into Checks with honest error and validity statements.
- **Methods.** Edit on `studies/**` and on Checks that consume study results, `evaluate.simulate` at both fidelities, `inspect.field`, `inspect.render` with overlays.
- **Exit Checks.**
  - `convergence_demonstrated`: at least three refinement levels, or Flux's error estimate below the study's stated tolerance.
  - `results_within_validity_envelope`, or the result is flagged and the Check severity reflects it.
  - `loads_trace_to_requirements`.
  - `signoff_fidelity_for_release_checks`.
  - `verification_case_passed`, where a std analytic benchmark exists for the physics.
- **Outputs.** Study definitions in Ingot, Checks on result Fields, and a simulation report: convergence table, error estimates, validity flags and overlay renders.
- **Failure behavior.** A result outside its `ValidityEnvelope` is never reported as a pass. The Check returns `error`, with the envelope violation as context.

### DFM reviewer

- **Purpose.** Find manufacturability problems for the declared process (machining, molding, sheet metal, additive) and suggest fixes.
- **Methods.** Read, Inspect, `evaluate.checks` with the `std::mfg::dfm` rule packages, `evaluate.manufacture` in estimate mode (phase 2), `propose.review`.
- **Exit Checks.** `every_finding_anchored` (to an `EntityId` and a source span); `every_blocker_has_fix_or_rationale`; `rules_version_recorded`.
- **Outputs.** A review with findings ranked by severity. Each finding names the rule, the measured value and the limit, and attaches a `SuggestedFix::ApplyEdits` where one exists.
- **Failure behavior.** The DFM reviewer cannot edit the design, which keeps finding and fixing separate. The author applies or rebuts each finding.

### CAM programmer

- **Purpose.** Produce machining programs: setups, fixturing, tool selection, strategies, toolpaths, simulation and posted NC code for a named machine.
- **Methods.** Edit on `mfg/cam/**`, `evaluate.manufacture`, `inspect.render` of toolpaths and material-removal states, `act.prepare` for `send_to_machine`.
- **Exit Checks.** `no_collisions` (tool, holder and fixture against stock and part); `no_gouges`; `stock_removed_within_tolerance`; `tools_in_library`; `feeds_within_tool_limits`; `posted_for_named_machine`.
- **Outputs.** A CAM program in Ingot, posted NC code and a setup sheet as derived artifacts in CAS, plus a strategy summary that lets a programmer accept or reject each operation.
- **Failure behavior.** The program is a proposal to a human programmer, operation by operation. CloudNC's CAM Assist works the same way: the programmer reviews and edits the proposed operations before toolpaths are created [S15]. Sending code to a machine is an Act that needs approval.

### Cost engineer

- **Purpose.** Estimate should-cost and price the BOM, then propose cost reductions.
- **Methods.** `evaluate.cost`, `read.catalog`, `evaluate.explore` on cost objectives, edit on `cost/**` and its own cost-reduction branches, `act.prepare` for `request_quote`.
- **Exit Checks.** `every_bom_line_priced_or_flagged`; `prices_have_source_and_date`; `totals_have_intervals`; `currency_stated`.
- **Outputs.** A cost report with per-line sources and intervals, plus cost-reduction Proposals, each with the cost delta and every Check margin it changes.
- **Failure behavior.** Supplier prices are untrusted data. They enter through quarantined extraction into typed fields, and their source is shown in every report.

### Drawing and MBD author

- **Purpose.** Produce drawings and model-based definition with complete product and manufacturing information.
- **Methods.** Edit on drawing source and PMI annotations, `evaluate.build`, `evaluate.checks` with `std::mbd` completeness Checks, `inspect.render`.
- **Exit Checks.** `every_feature_of_size_toleranced`; `datum_reference_frames_complete`; `annotations_reference_live_entities`; `views_do_not_overlap`; `pmi_semantic_in_ap242_export`.
- **Outputs.** Drawing sheets as Ingot drawing source, semantic PMI on the model, and a STEP AP242 export, using the AP242 writer that the tab owning `io/` specifies.
- **Failure behavior.** A missing tolerance becomes a finding for the detail designer. The author never invents a tolerance value.

### Catalog librarian

- **Purpose.** Curate catalog parts: import supplier data, normalize it into typed records, validate geometry against datasheets, deduplicate and link alternates.
- **Methods.** `read.catalog`, `read.external_text` through quarantine, edit on the catalog package repository, `evaluate.checks`, `act.prepare` for `publish_package`.
- **Exit Checks.** `key_dimensions_match_datasheet` (within each dimension's stated tolerance); `required_properties_present`; `units_typed`; `geometry_license_recorded`; `provenance_recorded`.
- **Outputs.** Proposals to the catalog repository: typed records, geometry, supplier data with source and date.
- **Failure behavior.** This role reads the most untrusted text. Its Proposals are always tainted and always need human review. Extracted values that fail validation are dropped and reported.

### Documentation writer

- **Purpose.** Write user documentation, assembly instructions and release notes from the design.
- **Methods.** Read, `inspect.describe`, `inspect.render`, edit on `docs/**` except drawings.
- **Exit Checks.** `every_number_cites_a_fact` (each value links to a `DescriptionFacts` entry); `facts_current_at_head`; `images_regenerate_identically`.
- **Outputs.** Markdown documentation with fact references and deterministic renders.
- **Failure behavior.** When a fact changes, CI marks every document that cites it as stale and opens a work item for the writer.

### Independent verifier

- **Purpose.** Act as the adversary: try to show that a Proposal is wrong, incomplete or under-checked.
- **Independence.** The verifier runs with a fresh context and no access to the author's transcript. It must not share session lineage with the author, and where policy requires, it uses a different model family.
- **Inputs.** It sees the requirements, the design, the semantic diff, the CI report and the rationale's structured fields: requirement ids, evidence ids and deviations. The free-text rationale is outside its delegation chain, so reading it taints the verifier session.
- **Methods.** Read, Inspect, Compare, all Evaluate methods on scratch branches forked from the Proposal head, `propose.review`, and `propose.create` for counter-proposals that add Checks.
- **Attack catalog.** Every review tries at least these:
  1. Requirements not covered by any Check.
  2. Worst-case tolerance stacks.
  3. Load cases and boundary conditions that the requirements imply but the studies omit.
  4. Material extremes.
  5. Check mutation (below).
  6. Query fragility.
  7. CI replay at a different platform class.
  8. Manufacturability under the declared process.
- **Check mutation.** The verifier applies seeded mutations: thin walls by 50%, remove fillets, double the loads, swap to the weakest permitted material. It confirms that the relevant Checks fail. A Check that passes under every mutation is reported as possibly vacuous.
- **Exit Checks.** `attack_catalog_covered`; `findings_reproducible` (each finding comes with an Ingot test that fails on the Proposal head); `mutation_score_reported`.
- **Outputs.** A review with a verdict, the attacks tried, findings with reproducing tests, a mutation score, and optional counter-proposals that add Checks.
- **Failure behavior.** The verifier cannot edit the reviewed branch. A verifier approval is required for every auto-merge.

**Decision D-AGT-12:** Every agent Proposal is verified by an independent verifier session that shares no lineage or context with the author and attacks the design with a fixed catalog, including Check mutation. *Why:* model self-review shares the author's blind spots; mutation testing turns "the Checks pass" into evidence that the Checks can fail. *Rejected:* self-verification only (Zookeeper-style snapshot review [S12] is useful but not independent); render-question verification only (CADCodeVerify reports a 7.30% reduction in point-cloud distance [S17], but rendered questions cannot detect a Check that cannot fail).

## Orchestration of swarms

A swarm is a tree of Proposals. A planner writes a plan of work items, and workers run each item on its own branch and deliver a child Proposal. A merge queue integrates children into an integration branch, and a verifier attacks the result before it reaches the target.

Agents coordinate only through repository objects, so every step is authenticated, versioned and visible to reviewers.

### When to use a swarm

Most changes need one agent. Anthropic reports that multi-agent systems use about 15× the tokens of chat and suit heavily parallel work, and that coding tasks parallelize less well [S33]. Design work is closer to coding than to broad research: most edits touch one feature tree.

**Decision D-AGT-13:** The default is a single agent; the runtime starts a swarm only when a validated plan has at least two work items that can run in parallel. Caps by default: 8 parallel workers per Proposal tree and a delegation depth of 2 (planner, then workers, which cannot spawn further agents). *Why:* cost grows faster than benefit when work is not parallel; Anthropic observed failure modes such as spawning 50 subagents for simple queries and duplicated work [S33]. *Rejected:* always-on swarms (cost, merge churn); unbounded recursive delegation (cost and accountability blur).

### Plans and work items

```rust
pub struct Plan {
    pub goal: String,
    pub items: Vec<WorkItem>,
    pub integration_branch: BranchName,  // agents/<proposal>/integration
    pub budget: Budget,                  // carved from the parent Proposal's budget
    pub max_parallel: u8,                // default 8
}

pub struct WorkItem {
    pub id: WorkItemId,                  // "w3"
    pub role: RoleRef,
    pub goal: String,
    pub requirements: Vec<RequirementId>,
    pub write_set: WriteSet,             // path globs and feature paths
    pub depends_on: Vec<WorkItemId>,
    pub acceptance: Vec<CheckRef>,       // must exist, or be added by the item, and pass
    pub budget: Budget,
    pub max_attempts: u8,                // default 3
    pub state: WorkItemState,
}

pub enum WorkItemState {
    Pending,
    Leased { session: SessionHandle, attempt: u8, lease_until: Timestamp },
    Proposed(ProposalId),
    Merged(RevisionId),
    Failed(FailureReport),               // typed errors from every attempt
    Cancelled,
}
```

`propose.plan` validates a plan before any work starts:

- The dependency graph is acyclic.
- Items that may run concurrently, meaning neither depends on the other, have disjoint write sets.
- Every item names acceptance Checks.
- Item budgets sum to no more than the plan budget.
- Every role exists, and an endpoint qualified for it is available.

Validation failures return `plan.invalid` with the offending items and a fix, such as adding a dependency between two items whose write sets overlap. A valid plan makes the server create the integration branch, owned by the planner's session, so the planner never needs `design:edit`.

The planner reads requirements and the trusted design, but never external text. This is the Plan-Then-Execute pattern: the actions are fixed before any untrusted data is processed, so tool outputs cannot change which actions run [S25]. Workers that must read untrusted documents do so inside their own items, where taint stays confined to that item's session and Proposal.

### Execution

[[DIAGRAM: swarm flow. Boxes: Human goal → Planner → Plan (validated by propose.plan) → Workers in parallel, one per work item, each on a child branch forked from the integration branch → child Proposals → Verifier (light) → Merge queue (CI on the merged result) → Integration branch → Parent Proposal → Verifier (full) → Human review or auto-merge policy → Target branch. Side arrows: every Evaluation goes to Kiln workers; budget flows Organization → Proposal tree → Work items → Sessions.]]

1. **Dispatch.** The runtime leases each ready item, one whose dependencies have merged, up to `max_parallel`. A lease opens a child session on a branch forked from the integration-branch head, with the item's write set, the role's scopes and a budget carved from the plan.
2. **Work.** The worker runs the role's loop: read, edit, build, check, inspect. It ends with a child Proposal targeting the integration branch.
3. **Light verification.** A verifier session reviews each child Proposal against attack-catalog items 1, 5 and 6: uncovered requirements, Check mutation and query fragility.
4. **Merge queue.** Child Proposals merge into the integration branch in dependency order. CI runs on each merged result, so the integration-branch head always passes every error-severity Check.
5. **Assembly.** When all items have merged, the planner updates the parent Proposal from the integration branch to the target, with a rationale linking each requirement to the items that address it.
6. **Full verification and review.** A verifier runs the full attack catalog on the parent Proposal, which then follows the Proposal and review flow below.

Integration branches are unprotected working branches. Merging children into them is not auto-merge, and the target receives only the parent Proposal, which goes through the full review flow.

Leases make the swarm crash-safe. A lease lasts 10 minutes and any API call from the session renews it. An expired lease returns the item to `Pending` with an incremented attempt number.

Writes from a session holding a stale attempt fail with `session.lease_lost`; the attempt number acts as a fencing token, so a stalled worker that wakes up cannot overwrite its replacement's work. Plan state lives on the parent Proposal and Evaluations are durable, so the crew runtime holds no state of its own and resumes from the repository after a restart.

### Coordination without messages

**Decision D-AGT-14:** Agents never message each other directly. Plans, work items, Proposals, reviews and anchored comments in the repository are the only coordination medium, and each is written through the API by an authenticated principal. *Why:* every coordination act becomes versioned, auditable and visible to humans; spoofed or replayed agent messages are a named risk (ASI07, Insecure Inter-Agent Communication [S30]); any MCP host can join a swarm without a second protocol. *Rejected:* direct messaging between agents, including A2A 1.0 [S51] (a second protocol whose messages live outside the design history); a shared scratch memory (unreviewed and poisonable, ASI06 [S30]).

A comment from another agent reaches the reader as untrusted text (see Safety). Agents therefore exchange facts through typed objects, such as failure reports, findings with reproducing tests and Check results, rather than through prose instructions.

### Conflict resolution

Conflicts are prevented first, then detected, then resolved by Checks rather than by model opinion.

| Stage | Mechanism | Outcome |
| --- | --- | --- |
| Prevention | Disjoint write sets for concurrent items, validated by `propose.plan` | Overlapping items run in sequence |
| Textual and semantic | `repo` semantic merge of a child into the integration branch | Clean merges proceed. A conflict on the same feature, parameter or entity sends the item back to its worker with the conflict as typed input. |
| Behavioral | Both children pass alone, but CI on the merged result fails a Check | The planner adds a reconcile item for a detail designer, with both diffs and the failing Check as inputs |
| Alternatives | Two items offer competing solutions that both pass | The plan's objectives rank them through `evaluate.explore`, or a deterministic metric comparison. A tie goes to a human. |
| Exhaustion | An item fails `max_attempts` times, or a reconcile item fails | The planner re-plans once. Then the human who started the work receives both alternatives side by side, with typed failure histories. |

### Design-space exploration

`evaluate.explore` searches a parametric design space for the best trade-offs, evaluating many variants in parallel through Kiln and Flux. Variants are parameter assignments recorded in an exploration record in CAS, not branches. `evaluate.materialize` turns a chosen variant into `SetParameter` edits on the session branch.

```rust
pub struct ExploreRequest {
    pub session: SessionHandle,
    pub rev: RevisionId,
    pub space: Vec<Variable>,
    pub objectives: Vec<Objective>,      // Minimize or Maximize an Ingot expression with a unit
    pub constraints: Vec<CheckRef>,      // default: every error-severity Check
    pub fidelities: Vec<FidelityLevel>,  // e.g. coarse build + interactive Flux, then sign-off
    pub strategy: Strategy,              // Auto | Sobol | Bayesian | Evolutionary | Grid
    pub batch: u16,                      // variants evaluated per round
    pub asynchronous: bool,              // default false; see determinism below
    pub budget: Budget,
    pub seed: u64,
}

pub enum Variable {
    Continuous { param: FeatureParam, lo: Quantity, hi: Quantity, log_scale: bool },
    Integer { param: FeatureParam, lo: i64, hi: i64 },
    Categorical { param: FeatureParam, choices: Vec<IngotExpr> },  // materials, catalog parts, layouts
}
```

The strategies come from the state of the art:

- **Initial design.** A scrambled Sobol sequence of 2(d+1) points by default, where d is the number of variables.
- **Expensive variants** (fewer than about 500 affordable, up to about 50 continuous variables): Bayesian optimization with Gaussian-process surrogates. qLogNEHVI is the acquisition for several objectives and qLogNoisyExpectedImprovement for one [S38]. The LogEI family fixes the numerical vanishing of expected-improvement acquisitions and matches or beats recent state-of-the-art acquisition functions [S37]. BoTorch 0.18.1 lists qLogNEHVI as a first-class multi-objective acquisition [S38].
- **High-dimensional spaces.** Surrogates use lengthscale priors scaled with dimension, a simple change that made vanilla Bayesian optimization outperform specialized high-dimensional methods on real-world tasks [S40].
- **Cheap variants, large budgets or mostly categorical spaces.** NSGA-II for two objectives and NSGA-III for three or more, both with constraint handling, as in pymoo 0.6.2 [S41].
- **Several fidelities, or objectives that can be computed separately** (phase 3). The hypervolume knowledge gradient decides which design, which objective and which fidelity to compute next, and is the one-step Bayes-optimal policy for hypervolume [S39]. Many Crucible objectives can be computed separately: cost and mass come from a cheap build, while stress needs Flux.

**Decision D-AGT-15:** Exploration strategies are implemented in Rust and published as the Wasm component package `std::explore`, matching BoTorch and pymoo as reference implementations instead of embedding them. *Why:* the contract puts heavy custom algorithms in Wasm components; Python and PyTorch cannot run deterministically in the evaluation sandbox, on every OS or in the browser. *Rejected:* a Python sidecar running BoTorch (no browser support, no determinism guarantee, a second runtime); only evolutionary methods (they need one to two orders of magnitude more variants [unverified as a general figure] when each variant costs a Flux solve).

Exploration rules:

- **Failure-aware search.** A variant that fails to build or resolve is recorded with its typed error. A Gaussian-process classifier models the probability of a successful build, and the acquisition is weighted by it. The report counts failures by error code; no variant is silently dropped.
- **Validity.** A result outside its `ValidityEnvelope` is flagged and excluded from the Pareto front by default, with an option to include it.
- **Fidelity ladder.** Screening runs at interactive fidelity. The top k Pareto points (default 5) are re-run at sign-off fidelity. A point is confirmed only when its sign-off result falls within the interactive error estimate. Otherwise it is flagged `fidelity_disagreement` and the surrogate is refit.
- **Ranking.** Non-dominated sorting gives the front, and hypervolume is measured against a reference point taken from requirement limits, or from the nadir plus 10%. Points are ordered by an augmented Chebyshev scalarization of the user's weights; with no weights, the knee point is highlighted. Ties break by variant id.
- **Determinism.** The optimizer receives its seed as input and fits Gaussian processes with deterministic L-BFGS from fixed Sobol restarts. By default it proposes variants in synchronous rounds of `batch`. Asynchronous mode refills a worker as soon as it frees up, which raises throughput but makes the proposal sequence depend on completion order. The report records which mode ran.
- **Cost.** Variants share upstream Ops, such as an unchanged sketch, so Kiln's cache lowers marginal cost. Admission control uses Kiln's per-variant estimate after expected cache hits.

### Budgets and scheduling on Kiln workers

Kiln owns Op scheduling, and this subsystem owns admission and accounting. Every Evaluation carries a priority class:

| Class | Used by | Preemption |
| --- | --- | --- |
| `interactive` | Sessions where a human is waiting, including the person's own edits | Never preempted |
| `agent` | Agent sessions | Preempted by `interactive` at Op boundaries |
| `ci` | Proposal CI and merge-queue runs | Preempted by `interactive` |
| `batch` | Explorations and benchmark runs | Preemptible by all; resumes from cached Ops |

Within a class, Kiln shares capacity fairly among principals, by each principal's dominant resource across CPU, GPU and memory. This is Dominant Resource Fairness [unverified: named from general knowledge; its paper was not opened]. Organization quotas come from policy.

GPU Ops, such as Flux GPU solves and non-deterministic renders, go to GPU workers. When no GPU is available, the CPU fallback runs and the report says so.

The planner sizes the swarm from Kiln's cost estimates and the budget. Model tiering is allowed: the planner and verifier may use the strongest qualified endpoint while workers use a cheaper one.

In Anthropic's research system, an Opus 4 lead with Sonnet 4 subagents outperformed a single Opus 4 agent by 90.2% on an internal research benchmark [S33]. Crucible treats this as a hypothesis to measure on golden tasks, not as a default.

## The Proposal and review flow

A Proposal is a branch plus rationale plus CI report [contract §2]. `repo` stores it as its pull request; a change order is a Proposal against a released configuration. This tab specifies the fields and rules that agent work needs, which humans' Proposals carry too.

### The Proposal object

```rust
pub struct Proposal {
    pub id: ProposalId,
    pub repo: RepoId,
    pub source: BranchName,
    pub target: BranchName,
    pub base: RevisionId,                // merge base, updated on rebase
    pub head: RevisionId,
    pub title: String,
    pub rationale: Rationale,
    pub author: Principal,
    pub delegation: Vec<Principal>,      // outermost first: the human who started the work
    pub parent: Option<ProposalId>,      // swarm child → parent
    pub plan: Option<Plan>,              // parent Proposals only
    pub ci: Option<CiReport>,            // for `head`; produced only by the CI service
    pub snapshots: Vec<Snapshot>,        // server-generated renders, pinned to `head`
    pub diff: SemanticDiffSummary,
    pub risk: RiskAssessment,            // computed by the server from the diff and labels
    pub labels: Labels,                  // taint, data provenance, data class
    pub reviews: Vec<Review>,
    pub state: ProposalState,            // Draft | Open { ready } | Merged(RevisionId) | Withdrawn | Superseded(ProposalId)
    pub usage: Usage,                    // total spent on this Proposal tree
}

pub struct Rationale {
    pub summary: String,                 // what and why, in plain words
    pub requirements: Vec<RequirementId>,// what the change addresses
    pub decisions: Vec<DesignChoice>,    // choice, alternatives considered, evidence (Evaluation ids)
    pub deviations: Vec<Deviation>,      // e.g. a query with stability below 1.0, and why
    pub limitations: Vec<String>,        // what the author knows is not covered
}
```

Preconditions for `propose.create` without `draft`, checked by the server:

1. The head builds at exact fidelity for every target.
2. Every Check passes, as the contract requires [contract §7]. An author who believes a Check should not apply changes or waives it in source and explains why under `deviations`. Changing or waiving a Check is a loosening, so the Proposal is R3 (D-AGT-16).
3. Snapshots exist for the head: a `Grid4` render of each changed Part or Assembly, a geometry-overlay diff render, and a Field-overlay render for each changed study result. The server generates them on the deterministic path, so an agent cannot attach a misleading image.
4. The rationale has a summary. When the repository declares requirements, it also links at least one.
5. Every change on the branch carries complete provenance.

A failure returns `propose.preconditions_failed` with the failing items and fixes. Draft Proposals skip items 1 to 3 so that people can discuss work in progress. A draft cannot be reviewed for merge, auto-merged or merged.

### CI report

The CI service runs as `service:ci`, from the head revision, and writes the `CiReport`. No agent can write or edit it. `evaluate.ci` gives agents the identical report in advance, so they never discover a CI failure for the first time at review.

```rust
pub struct CiReport {
    pub revision: RevisionId,
    pub lockfile: Sha256,
    pub platform_classes: Vec<PlatformClassResult>, // build and check outcomes per class
    pub cross_platform: AgreementReport,             // results agree within declared tolerance
    pub checks: Vec<CheckOutcome>,                   // value, margin, severity, oracle source
    pub margin_deltas: Vec<MarginDelta>,             // vs the target's head
    pub metrics: Vec<MetricDelta>,                   // mass, cost, cycle time, declared objectives
    pub validity: Vec<ValidityFlag>,                 // any Flux result outside its envelope
    pub oracle_integrity: OracleIntegrity,           // protected oracle paths untouched or approved
    pub cache: CacheStats,
    pub usage: Usage,
}
```

The tab that specifies `repo` owns hardware CI on every commit [contract §7]. This tab requires the fields above. Before auto-merge it also requires two runs per Proposal, on the primary platform class and on a second one, which tests cross-platform agreement within declared tolerance.

### Risk classification

The server classifies every Proposal from its semantic diff and labels. No model takes part in the classification.

| Class | Meaning | Examples |
| --- | --- | --- |
| R0 | No semantic change | Formatting and comments (identical IR hash), documentation text, regenerated renders |
| R1 | Contained design change | Parameter changes within declared ranges on unreleased designs; no Check, tolerance, BOM or dependency changes; no margin falls below 90% of its target-head value |
| R2 | Ordinary design change | New features, new Checks, material changes, BOM changes, new studies, dependency updates that keep Op behavior versions |
| R3 | Sensitive change | Checks removed or loosened, tolerances loosened, oracle references changed, protected paths touched, Op behavior-version bumps in the lockfile, change orders on released configurations, any tainted Proposal |
| R4 | Critical | Changes that feed an Act class: a release candidate, NC code bound for a machine, files bound for a supplier; any change to policy files |

**Decision D-AGT-16:** Risk class is a deterministic function of the semantic diff, labels and target, computed by the server. Loosening any Check or tolerance, and any tainted content, is at least R3. *Why:* an agent that loosens a Check to make it pass is the cheapest form of reward hacking, so it must always reach a human. *Rejected:* model-assessed risk (manipulable and non-reproducible); a single class for all agent work (forces review fatigue on trivial changes, ASI09 [S30]).

### Human review

The review view, specified by the UIX tab, shows the feature diff, geometry overlay, metric deltas and source diff [contract §7]. For agent Proposals it adds:

- The provenance panel: agent, role and version, model endpoint (attested or declared), instructions digest with a link to the full instructions, and the delegating human.
- The risk class and the diff items that set it.
- Taint markers: which external texts the authoring sessions read, with their origins.
- The verifier report: attacks tried, findings with reproducing tests, and the mutation score.
- Budget used, and the canonical text description of the change from `inspect.describe`.

Reviewers approve, request changes or comment. Findings anchor to `EntityId`s, feature paths or source spans, and they return to the author agent as typed input. Agents may answer findings with comments; reviewers see those comments marked as agent-authored.

Separation of duties:

- No principal in a Proposal's delegation chain may approve it, except the delegating human, and only for R0 to R2 by default.
- R3 and R4 need approval from a human outside the delegation chain, a two-person rule. Repository policy can require more reviewers.
- Agent reviews, from the verifier or the DFM reviewer, never count toward human approval requirements.

### Auto-merge policy

Auto-merge is a repository policy and is off by default. Only humans with `policy:admin` change it, through a reviewed Proposal.

```rust
pub struct AutoMergePolicy {
    pub enabled: bool,                   // default false
    pub classes: Vec<RiskClass>,         // allowed: R0 and R1 only; R2+ rejected at policy validation
    pub targets: Vec<BranchPattern>,     // never release branches or tags
    pub require_verifier_approval: bool, // always true; field kept for explicitness
    pub require_untainted: bool,         // always true
    pub max_geometry_deviation: Length,  // e.g. 0.5mm Hausdorff
    pub max_cost_increase: Ratio,        // e.g. 1%
    pub require_second_platform_class: bool, // default true
    pub quiet_period: Duration,          // default 10 min: watchers notified, any may veto
    pub max_per_day: u32,                // default 20 per repository
}
```

A review from a tainted session never satisfies an auto-merge condition.

**Decision D-AGT-17:** Auto-merge is possible only for R0 and R1 Proposals that are untainted, approved by an independent verifier, CI-green on two platform classes and unvetoed through a quiet period. R2 and above always need a human. *Why:* low-risk changes should not queue behind people, but anything that can change behavior meaningfully needs accountability. *Rejected:* auto-merge on "all Checks pass" alone (Checks can be incomplete; mutation testing exists because of that); no auto-merge ever (review fatigue degrades human attention on the Proposals that matter).

Auto-merges are performed by `service:merge` after the quiet period, never by the authoring agent. The change provenance records the policy version that allowed the merge.

An organization-wide agent freeze stops auto-merge, new agent sessions and all agent writes within 5 seconds (target). It is the kill switch for an incident.

### Provenance of agent changes

Every `repo` change records who made it and why. The API server writes the record and signs it, so the agent cannot forge its own record.

```rust
pub struct ChangeProvenance {
    pub change: ChangeId,
    pub principal: Principal,
    pub delegation: Vec<Principal>,
    pub session: SessionId,
    pub role: Option<(RoleRef, Sha256)>,         // role version and skill manifest digest
    pub endpoint: Option<EndpointRecord>,        // provider, model id, version if known, region
    pub endpoint_assurance: Assurance,           // Attested (hosted crew) | Declared (external host)
    pub instructions: Sha256,                    // goal + work item + role skill + system prompt; stored in CAS
    pub client: ClientInfo,                      // from MCP `io.modelcontextprotocol/clientInfo`
    pub inputs: Vec<ReadRecord>,                 // digests of what the session read before this change
    pub taint: Taint,
    pub api_log: CasRef,                         // every API call of the session up to this change
    pub transcript: Option<CasRef>,              // model transcript: hosted crew always; external hosts if uploaded
}
```

Each record is wrapped as an in-toto Statement v1, with `_type` `https://in-toto.io/Statement/v1`, the change digest as `subject`, and a Crucible-defined `predicateType` [S48]. The deployment's provenance key signs it.

Crucible can attest the model only when its own crew runtime made the model call. For external MCP hosts, the model identity is whatever the client declares, so it is marked `Declared` and the review UI says so. Instruction texts and transcripts are stored in CAS under the session's data class and retention policy, because they may contain confidential design intent.

### Reversibility

| Effect | How it is undone | Limit |
| --- | --- | --- |
| Change on an agent's own branch | `edit.reset_branch` or `edit.revert` | None; branches are cheap |
| Merge into a protected branch | `edit.revert` of the merge, recorded as a forward change; one click in the UI | Downstream merges may conflict; the revert is a Proposal like any other |
| Swarm result | Revert the parent Proposal's merge, which reverts the whole swarm | Same as above |
| Auto-merge | Same as a merge. Auto-merged changes are listed in a daily digest with revert links. | — |
| Release (signed tag) | Not undoable. Superseded by a change order and a new release. | By design |
| Act with a reversible or compensable class | Withdrawal or cancellation through the integration, recorded as a new Act | Depends on the external party, stated in the ActionPlan |
| Irreversible Act (files sent, NC program run) | Not undoable | Hence human approval of the exact action |

History is never rewritten on protected branches. An erroneous agent change stays visible in history with its provenance and its revert.

## Safety and security

Prompt injection is not solved. Meta calls it "a fundamental, unsolved weakness in all LLMs" [S28], and OWASP lists it first among LLM application risks [S29]. Crucible therefore does not rely on any model resisting it.

The server enforces every boundary deterministically. Authority comes only from authenticated principals and grants, and untrusted content is labeled and tracked. Labels restrict what a session may do, and every real-world effect needs a human to approve the exact action.

### Threat model

| Threat | OWASP agentic risk [S30] | Primary controls |
| --- | --- | --- |
| Instructions hidden in STEP text, datasheets, supplier data, comments, catalog records or requirement documents | ASI01 Agent Goal Hijack | Data/instruction separation, taint labels, quarantined extraction |
| Agent misuses a legitimate method | ASI02 Tool Misuse | Scopes, write sets, risk classes, Act approvals |
| Stolen or escalated agent credentials | ASI03 Identity & Privilege Abuse | Audience-bound tokens, per-session downscoped tokens by token exchange, handles bound to principals |
| Malicious MCP servers, skills or packages | ASI04 Agentic Supply Chain | Pinned skill manifests, package signatures, no third-party MCP servers in hosted sessions by default |
| Sandbox escape from agent-supplied code | ASI05 Unexpected Code Execution | Agents run no code except Ingot and Wasm components in Kiln's sandbox, which has no clocks, randomness, files or network |
| Poisoned memory or context | ASI06 Memory & Context Poisoning | No shared agent memory; context rebuilt from the repository; external text labeled |
| Spoofed agent-to-agent messages | ASI07 Insecure Inter-Agent Communication | No direct messaging (D-AGT-14) |
| Cascading failures across a swarm | ASI08 Cascading Failures | Budgets, attempt limits, merge-queue CI, organization freeze |
| Over-trust by reviewers | ASI09 Human-Agent Trust Exploitation | Risk classes, verifier reports, deterministic summaries, approval screens built from typed data |
| Agent acts outside policy | ASI10 Rogue Agents | Server-side enforcement, audit, anomaly alerts, freeze |
| Exfiltration of design data | — | Data classes, endpoint clearance, egress rules |

### Untrusted content is data

**Decision D-AGT-18:** Content from outside the trust boundary is labeled `untrusted` at ingestion and keeps that label through every derivation. Untrusted content can never become instructions: the API returns it only as typed `ExternalText` values with origin metadata, and any session that reads its raw text becomes tainted. A tainted session cannot perform consequential actions without a fresh human approval. *Why:* defenses with provable resistance constrain an agent after it ingests untrusted input, so that the input cannot trigger consequential actions [S25]. *Rejected:* detection classifiers or delimiter "spotlighting" as primary controls (probabilistic; kept only as monitoring signals); trusting frontier models to ignore embedded instructions (no guarantee).

Untrusted origins:

- Text inside imported files: STEP names, notes and property strings; PDFs; spreadsheets.
- Supplier and catalog data, including datasheets, quotes and descriptions.
- Web content.
- Comments and descriptions written by principals outside the delegation chain, including other agents.
- Package READMEs and docs from unverified publishers.
- Model outputs from quarantined extraction.

Trusted origins:

- The goal text from the delegating human.
- Role skills whose manifest digest is pinned.
- Ingot source on protected branches.
- Std documentation shipped with the signed release.

A design's Ingot source is trusted for structure, but string literals that came from imports are wrapped as `external("...")` by the importers, so their text stays untrusted.

Labels follow the FIDES model of information-flow control. Every value carries an integrity label (`trusted` or `untrusted`) and a confidentiality label, and derived values take the most restrictive combination of their inputs [S27].

Crucible's confidentiality labels are its data classes. Labels attach to API responses and to derived artifacts in CAS, so a render of a model containing an untrusted STEP name stays untrusted.

Three rules make labels workable in practice:

- **Instruction-capable content.** Only free text and images can carry instructions. Typed numbers with units, enums, `EntityId`s and identifiers that Crucible generates cannot, so untrusted values of those kinds keep their label but do not taint a session that reads them.
- **Endorsement.** When a human approves and merges a tainted Proposal, its content becomes trusted on the target branch. This covers geometry, parameters and source the human reviewed. Human review is the only way untrusted content becomes trusted.
- **External strings stay external.** `external(...)` literals are never endorsed. Their text stays untrusted on every branch, forever.

The residual risk is an injection that a human reviewer endorses without noticing. Review shows taint sources and highlights text that came from them, but that risk cannot be removed entirely.

### Taint and the Rule of Two

Meta's Rule of Two names three properties: processing untrustworthy inputs, access to sensitive systems or private data, and the ability to change state or communicate externally. An agent should have no more than two of them in one session [S28]. Crucible applies the rule through labels.

| Session state | May read untrusted text | May edit own branch | May propose | May merge, auto-merge or commit an Act |
| --- | --- | --- | --- | --- |
| Clean | Only by becoming tainted | Yes | Yes | Yes, subject to policy |
| Tainted | Yes | Yes | Yes; the Proposal is labeled tainted and is R3 or higher | No. Needs a human approval that names the taint sources. |

A tainted session holds all three of the Rule of Two's properties, but only in a narrow form: its only state changes are writes to its own unprotected branch and Proposals. When all three properties are present, the rule calls for supervision instead of autonomy [S28], and human review of tainted Proposals provides it.

A tainted session can still do useful work, such as importing a supplier model or reading a datasheet into typed fields. Its output goes to human review instead of directly into a consequential action.

Taint never clears inside a session. To act cleanly again, an agent opens a new session, which starts with a fresh context.

### Quarantined extraction

When a role needs facts from untrusted documents, it uses the Dual LLM pattern [S25]. A quarantined model with no tools reads the text and fills a typed schema. The privileged agent sees only the validated typed values.

```rust
pub struct ExtractRequest {
    pub source: ExternalTextHandle,
    pub schema: ExtractSchema,           // Ingot record type: Quantities with units, enums, bounded strings
    pub instructions: TemplateId,        // fixed, versioned templates; never agent-written prose
}
```

Extraction rules:

1. The quarantined call carries no tools and no other context, and it produces only JSON that is validated against the schema.
2. Strings in the output are bounded in length and remain labeled untrusted. Numbers must carry units and are range-checked against the schema.
3. Extracted values enter the design only through Proposals, which inherit the taint.
4. The catalog librarian cross-checks extracted dimensions against geometry whenever both exist.

Microsoft's FIDES implementation in Agent Framework uses a tool-free quarantined LLM for the same purpose and calls its output untrusted [S27]. Crucible runs extraction as the server-side helper `std::agents::extract`. It uses the deployment's quarantine endpoint, which is configured per data class and is always independent of the calling agent's host.

### Permission scopes, write sets and protected branches

The Scopes table under Built-in roles lists the scopes, and grants intersect as described under Sessions, identity and delegation. In addition:

- **Write sets** confine edits to path and feature-path globs. Violations fail before anything is recorded.
- **Protected branches.** `main`, `release/*` and every branch a policy names reject direct writes from any principal; they change only through Proposals. Agent sessions cannot be opened on them.
- **Protected paths.** `oracles/**`, policy files, `.crucible/policy.ingot` and lockfile behavior-version pins reject agent writes outside Proposals and always raise a Proposal to R3 or R4. Agents can read `oracles/**` but never write it, as the contract requires [contract §7].
- **Tolerance loosening** needs human approval [contract §7]; it is R3 by D-AGT-16.

### Cost caps

Budgets are described under Rate, cost and size limits. Hard caps are enforced at admission, so an Evaluation that would exceed the remaining budget never starts.

Organization policy sets a ceiling per agent session (default 25 USD), per Proposal tree (default 200 USD) and per day (default 1,000 USD). Humans can raise them, and an increase is audited. An anomaly alert fires within a minute when a session spends more than three times the median for its role and task size.

### Data classes and model endpoints

Every repository, file and derived artifact has a data class. Policy defines the classes. The defaults are `public`, `internal`, `confidential` and `export_controlled`, and `export_controlled` has subclasses per regime, such as EAR ECCN or ITAR USML category.

**Decision D-AGT-19:** Every model endpoint carries a clearance per data class, granted by the organization's administrator. A session's clearance is the minimum of the human's, the endpoint's and the repository's, and the API refuses to return content above that clearance. *Why:* export control and confidentiality are properties of the data, so enforcement belongs where the data leaves, which is the API response. *Rejected:* trusting MCP hosts to filter (Crucible cannot see what an external host forwards); per-prompt redaction by a model (unreliable).

For external MCP hosts, clearance attaches to the OAuth client identity that the organization registers, meaning its Client ID Metadata Document URL [S6]. Unregistered clients receive the policy default, which is `internal` unless set lower.

Crucible provides mechanisms; it does not decide what is lawful. The organization decides which endpoints are cleared. Two US carve-outs illustrate the requirement:

- Under the EAR, sending or storing unclassified technology is not an export when two conditions hold [S49]. It is end-to-end encrypted with cryptographic modules compliant with FIPS 140-2 or its successors, and it is not intentionally stored in a Country Group D:5 country.
- Under the ITAR, the parallel carve-out also requires end-to-end encryption with FIPS 140-2 cryptography or an equivalent of at least AES-128 strength. The data must not be sent to or stored in a proscribed country, and no third party may hold the means of decryption [S50].

A hosted model provider decrypts prompts to process them. The condition that no third party holds the means of decryption therefore does not obviously hold for a hosted model [unverified: legal interpretation; not legal advice]. The defaults follow from that:

- `export_controlled` content is cleared only for local models, or for endpoints the organization attests are inside its own security boundary.
- Hosted crew sessions with a cleared endpoint record the endpoint's region with every model call.
- Air-gapped deployments run the crew against local models only.

When content above clearance is needed, the API returns `label.class_exceeds_clearance`. The error names a cleared endpoint where one exists, and otherwise suggests asking a human. Partial results show where redacted content was and why.

### Exfiltration controls

Exfiltration needs a channel. Crucible closes or watches each one:

| Channel | Control |
| --- | --- |
| Model context of an uncleared endpoint | Clearance enforcement in API responses (D-AGT-19) |
| Act methods that send files or messages | Human approval of the exact recipients and file digests; data class checked against recipient clearance |
| URLs in agent output | Links in Proposals and comments render as inert text unless their domain is allowlisted; images from external URLs are never loaded in review |
| Wasm components in evaluation | No network, files or clocks [contract §7] |
| Hosted crew runtime | Egress only to the API and to cleared model endpoints; no general web access unless a role needs it and policy grants it |
| Read volume | Anomaly detection on bytes read per session against the role baseline; alert and optional automatic freeze |
| Third-party MCP servers in a hosted session | Off by default; allowlisted by `policy:admin` per server identity |

For external MCP hosts, Crucible cannot see or control what the host does with returned content. Clearance enforcement at the response is therefore the boundary, and the audit log records exactly what was returned to which client.

### Irreversible real-world actions

Act methods cover every effect outside the design repository. Each Act class declares its reversibility, cost model and recipients.

| Act class | Example | Reversibility |
| --- | --- | --- |
| `release` | Create a signed release tag; release to manufacturing | Irreversible (superseded by a change order) |
| `send_to_supplier` | Send a STEP and drawing package for quotation or production | Irreversible |
| `request_quote` | Send an RFQ to suppliers through an integration | Irreversible |
| `order` | Place a purchase order for catalog parts | Compensable (cancellation per supplier terms) |
| `send_to_machine` | Transfer posted NC code to a machine controller | Irreversible once run |
| `publish_package` | Publish a package version to the registry | Yanking possible; the version stays reserved |
| `share_external` | Share a repository or Proposal with an outside organization | Revocable access; copies may persist |
| `notify_external` | Email or post outside the organization | Irreversible |

**Decision D-AGT-20:** Every Act is two-phase. `act.prepare` produces a deterministic `ActionPlan` with a digest. `act.commit` executes only after a human with the right authority approves that digest through an out-of-band URL elicitation with step-up authentication. *Why:* the human must approve exactly what will happen, rendered from typed data and not from model prose; a URL-mode elicitation is an out-of-band interaction whose outcome the client learns only by retrying [S2][S5], so the approval never passes through the agent's channel. *Rejected:* an MCP form elicitation answered in the agent's host (the agent's client mediates it, so a compromised host could answer it); a standing pre-approval for Act classes (approves actions nobody has seen).

```rust
pub struct ActionPlan {
    pub digest: Sha256,                  // over the canonical plan
    pub class: ActClass,
    pub summary: String,                 // template-rendered from the fields below
    pub effects: Vec<Effect>,            // e.g. SendFiles { recipient, files: [(name, sha256, class)] }
    pub recipients: Vec<VerifiedRecipient>,
    pub cost: Option<Money>,
    pub reversibility: Reversibility,
    pub data_classes: Vec<DataClass>,
    pub from: RevisionId,
    pub requested_by: Vec<Principal>,    // delegation chain
    pub taint: Taint,
    pub expires: Timestamp,              // default 24 h
}
```

The approval screen comes from the plan's typed fields, never from agent text. It shows the files with digests and data classes, the recipients with verification status, the cost, the reversibility and the full delegation chain.

A plan that changes between approval and commit fails with `act.plan_changed`. Approvals are single-use and are recorded in the audit log with the approver's identity and authentication method.

Approval requests reach the delegating human, or an approver with the required authority, through the review UI and Tier 2 notifications. This also covers hosted crew sessions that have no human client attached.

A client that does not support elicitation receives `act.approval_pending` with the approval URL in `context`, and the agent polls `act.status`. The approval itself always happens on Crucible's own page, never inside the agent's channel.

[[DIAGRAM: Act two-phase sequence. Lanes: Agent, api server, Approver (Crucible approval page with step-up), External system. Arrows: Agent → act.prepare → server returns ActionPlan with digest; Agent → act.commit(digest) → server returns InputRequiredResult with URL elicitation; Approver opens URL → step-up authentication → approves digest; Agent retries act.commit with requestState → server verifies approval, plan unchanged, recipients verified → executes against External system → ActionReceipt; audit record written at each step.]]

Recipients must be verified records in the organization's supplier registry, which `repo` stores and the MFG tab specifies. A recipient that appears only in agent-supplied text is rejected with `act.recipient_unverified`. Release Acts also require the release policy from `repo`: a signed tag, all Checks passing at sign-off fidelity, and the required approvers.

### Audit

Every API call creates an audit record: principal, delegation chain, session, method, argument digest, result status, labels, cost, client info and trace id. Records are append-only and form a hash chain, whose head is signed and anchored in the repository every hour.

Retention is set by policy, with a default of seven years for repositories that contain releases [unverified: chosen as a common records-retention period, not taken from a cited regulation].

`read.audit` exposes records to holders of `audit:read`. Exports use OpenTelemetry for traces and JSON Lines for records. Audit records hold digests rather than content, except for Act plans, approvals and policy changes, which are stored in full.

## Model independence

Crucible works with any model, because every guarantee lives in the server. Models differ in how well they do the work, never in what they are allowed to do.

### Two ways to bring a model

1. **External host.** Any MCP 2026-07-28 client connects to Crucible's MCP server: a desktop assistant, an IDE agent, or a custom agent built on a provider SDK. The host owns the model loop. Crucible enforces scopes, labels, budgets and approvals on every call.
2. **Hosted crew.** `apps/crew` runs Crucible's own model loop for roles and swarms, inside the deployment, against configured model endpoints. It reaches Crucible only through the public SDK.

**Decision D-AGT-21:** The hosted crew calls models through one Rust trait, `ModelEndpoint`, with adapters for major hosted APIs and for local OpenAI-compatible servers. Crucible does not use MCP Sampling. *Why:* MCP 2026-07-28 deprecates Sampling and advises integrating with provider APIs directly [S2]; one trait keeps provider choice a configuration decision. *Rejected:* Sampling through the client (deprecated); a single provider (founder requirement and air-gapped installs).

```rust
pub trait ModelEndpoint: Send + Sync {
    fn id(&self) -> &EndpointId;
    fn capabilities(&self) -> &ModelCapabilities;   // tool calling, vision, context tokens, structured output
    fn clearance(&self) -> &Clearance;              // data classes and regions
    async fn complete(&self, req: CompletionRequest) -> Result<CompletionStream, ModelError>;
}

pub struct ModelCapabilities {
    pub tool_calling: ToolCalling,       // Native | JsonMode | None
    pub vision: bool,
    pub context_tokens: u32,
    pub max_output_tokens: u32,
    pub structured_output: bool,         // schema-constrained decoding
    pub qualified_roles: Vec<(RoleRef, QualificationRecord)>,
}
```

### Qualification and graceful degradation

An endpoint qualifies for a role when it passes that role's qualification suite: a subset of the golden tasks at a pass threshold, recorded with the date and suite version. A role's `ModelRequirements` lists the capabilities it needs and its qualification threshold.

| Missing capability | Degradation |
| --- | --- |
| Vision | Renders are replaced by `visible_summary` text, structured marks and `inspect.describe`. The role runs if it is qualified in text-only mode, which the suite tests separately. |
| Native tool calling | JSON-mode tool calling with schema validation and up to 2 repair retries; endpoints without either are not qualified |
| Long context | Smaller page sizes, outlines before source, and stricter `detail: "concise"` defaults |
| Structured output | Validation and repair retries; extraction falls back to a qualified endpoint or fails |
| Endpoint unavailable | Retry with backoff, then fail over to the next qualified endpoint in the role's list. The change provenance records the switch. |
| No qualified endpoint | The role is unavailable, with error `crew.no_qualified_endpoint` and the qualification results. Never a silent downgrade. |

Local models are first-class. Air-gapped deployments configure local endpoints, run the qualification suite on site, and see per-role results.

The founder's requirement of identical behavior across platforms applies to Crucible's side: the same calls give the same results on every OS. Model outputs are not deterministic, so Crucible makes no claim of identical model behavior. Instead, every agent output is turned into Ingot or typed records that deterministic Checks verify (invariant 5).

Each hosted-crew model call records a replay record in CAS: the endpoint, the request digest, the parameters including temperature and seed where supported, and the response. Benchmarks and incident reviews can then replay a session's API calls exactly, even when the model cannot be re-run.

## Benchmarking agents

Agent quality is measured, versioned and gated like any other feature. The harness, task suites and graders live in `oracles/agents/`, which agents can read but not write. The held-out suites are not stored in any repository that agents can access, so agents cannot see them [contract §7].

### Benchmarks

| Suite | What it measures | Source and size | Use |
| --- | --- | --- | --- |
| Text2CAD-Bench | Text to parametric CAD across 4 levels (L1–L2 basic, L3 complex topology and freeform, L4 non-mechanical) | 600 examples with geometric and procedural prompts; models write CadQuery; metrics are Chamfer Distance, Invalidity Rate, IoU, and a VLM rubric for L4 [S16] | External comparability. Crucible adapts the task: the agent writes Ingot, and Crucible scores the exported geometry with the paper's metrics. |
| CADPrompt | Text to CAD code | 200 prompts with expert-annotated code; point-cloud distance and compile success [S17] | External comparability, scored the same way |
| CADTestBench | Text to CAD verified by executable tests of geometric and topological requirements | Code and data on GitHub and Hugging Face [S18] | Closest in spirit to Crucible's Check-based grading; adopted as a reference |
| MUSE | Manufacturable, functional and assemblable B-rep assemblies | Three-stage funnel: code validity, geometric validity, then a rubric judge for intent [S19] | Phase 2+. Strongest models scored 19–21% on fine-grained engineering criteria [S19]. |
| Golden-product tasks | Real tasks on golden products 1–6: create, edit, fix a failing Check, add a study, DFM fix, CAM program, change order | Grows each phase; at least 50 tasks per golden product (target) | Primary internal metric and release gate |
| Held-out set | Same task kinds on products never shown to agents or their developers | At least 200 tasks by phase 2 (target); refreshed 20% per year | Overfitting control; release gate |
| Injection suite | Golden tasks with injected instructions in STEP text, datasheets, comments and catalog records | 100 or more attacks per release (target), following the AgentDojo methodology [S34] | Security gate |

The public benchmarks were not designed for Ingot. Crucible reports them as adapted variants and publishes the adaptation code. Text2CAD-Bench's evaluation code had not been released when the paper appeared ("will be released after accept"), so Crucible reimplements its metrics from the paper's definitions [S16].

### Grading

Golden tasks are graded by Checks, never by model opinion, wherever possible. Each task ships with:

- A starting revision and a goal.
- Acceptance Checks hidden from the agent: the visible Checks plus held-out ones.
- A reference solution with its edit size.
- Forbidden actions, such as loosening a Check or touching oracles.

Grading runs in `service:ci` on two platform classes. A model judge is used only for documentation quality and requirement-text fidelity.

The judge's rubric scores 0.0–1.0 with pass or fail, the format Anthropic found closest to human judgment [S33]. It always uses a model family different from the agent's, and a human calibration set checks it every release.

### Metrics

| Metric | Definition |
| --- | --- |
| Task success | All acceptance Checks pass, including hidden ones, and no forbidden action occurred |
| pass^k | Crucible's definition: the probability that all k independent trials of a task succeed, reported for k = 1 and 4. τ-bench introduced pass^k to measure reliability across trials, and found pass^8 below 25% in its retail domain for state-of-the-art function-calling agents [S35]. |
| Checks passed | Fraction of acceptance Checks passed, including on failed tasks |
| Edit minimality | Ratio of the agent's semantic diff size (features, parameters and lines touched) to the reference solution's; lower is better, 1.0 matches the reference |
| Query robustness | Fraction of queries the agent introduced with stability score 1.0 |
| Review acceptance | For live use: fraction of agent Proposals merged without requested changes, and the median number of review rounds |
| Verifier catch rate | Fraction of seeded defects in a planted-defect set that the verifier finds |
| Cost | Total `Usage`, including model tokens and compute, per successful task |
| Time | Wall-clock time to a ready Proposal |
| Injection resistance | Utility under attack, and the rate of successful attacks, where success means an attacker-chosen consequential action |
| Safety violations | Attempted scope violations, write-set violations and forbidden actions per 100 tasks (target 0 completed) |

### Regression benchmarking per release

Every Crucible release and every change to `std::agents`, the crew runtime or the MCP surface runs these gates:

1. Golden tasks and the held-out set on every qualified endpoint, at 3 trials per task.
2. Comparison against the previous release, per suite and per metric.
3. A gate fails if task success drops by more than 2 points (target) at 95% confidence by a paired bootstrap, or if any injection succeeds.
4. Results are published as a release artifact with every task's transcript, kept under the held-out set's access rules.

When an endpoint changes version, it is re-qualified before roles use it again.

### Red-teaming

- **Continuous automated attacks.** The injection suite grows with every incident and every new import format. Attacks are adaptive: an attacker model rewrites failed attacks against the current defenses, following AgentDojo's design as an extensible environment for adaptive attacks [S34].
- **Scheduled human red-teaming** before each phase gate, covering the threat-model table and the Act approval flow.
- **Bounty.** A public bounty for injection-to-Act chains, from phase 3 [unverified: program terms to be set by the organization].
- **Tripwire values.** Sentinel strings in test repositories detect exfiltration in benchmark runs.

## Training and adaptation data

Crucible adapts models through context first (skills, docs, examples) and uses fine-tuning only where measurement shows a gain. Any data used for training must have a clear license and a recorded provenance.

### Procedural data generation

Crucible generates training and benchmark data from its own engine:

- **Programs.** Random but valid Ingot programs from a grammar of std features with sampled parameters. CAD-Recode trained on one million procedurally generated CAD sequences written as Python code and reported outperforming earlier methods on DeepCAD, Fusion 360 and CC3D [S20]. Crucible generates Ingot instead.
- **Edits.** Mutations of valid programs paired with natural-language descriptions generated from the semantic diff. The descriptions are template-generated and then optionally paraphrased by a model.
- **Repairs.** Programs with injected errors (unit errors, resolve failures, failing Checks) paired with their fixes, in the format of the error catalog.
- **Observations.** Renders with marks, sections and Field overlays paired with structured facts.

Every generated item is built and checked. Only items that build, with known answers, enter the corpus. The generator is deterministic from a seed, and the corpus is reproducible from (generator version, std version, seed range).

### Licensing constraints

| Source | Terms | Crucible use |
| --- | --- | --- |
| Fusion 360 Gallery Dataset | Non-commercial research only; no redistribution of the whole dataset; no re-association of models with creators; license terminable by Autodesk [S21] | No use in commercial training or shipped benchmarks. Research comparisons only, by a research group whose outputs do not ship. |
| ABC dataset | Copyright held by creators; licensing by reference to Onshape Terms of Use 1.g.ii [S22]. Those terms grant a broad license, including commercial use, for Free Plan public documents created on or after 7 August 2018, or earlier ones without a LICENSE tab; documents with a LICENSE tab may reserve greater rights [S23]. | Use only after per-model filtering by document date and LICENSE tab, with legal review. Excluded until filtering is verified. |
| DeepCAD and derivatives | Built from ABC [unverified] | Same as ABC |
| Text2CAD-Bench, CADPrompt, CADTestBench, MUSE | Licenses not stated on the pages opened [S16][S17][S18][S19] | Evaluation only, after license review; never training |
| Crucible procedural data | Generated by Crucible | Unrestricted |
| std and golden products | Open source, under the std license | Unrestricted |
| Customer data | Owned by the customer | Opt-in only (below) |

**Decision D-AGT-22:** Crucible trains and adapts only on procedural data, its own open-source std and golden products, data with verified commercial-use licenses, and customer data under explicit opt-in. Non-commercial datasets are excluded from anything that ships. *Why:* model weights inherit data obligations; the Fusion 360 Gallery license forbids commercial use [S21]. *Rejected:* "research use" of restricted data for shipped models (license violation); scraping public CAD models (terms of use and copyright).

### Customer data

- **Off by default** for every organization, repository and data class.
- **Opt-in** is per repository, by an organization administrator, with a stated purpose: improving the crew for everyone, or adapting a private endpoint only for that organization.
- **Never eligible:** `export_controlled` repositories, under any setting.
- **Scrubbing.** Names, comments and external text are removed or replaced before training, keeping geometry, Ingot structure and edit patterns. Removing text also removes injected instructions from the training data.
- **Withdrawal.** Opt-out stops future collection, and data already used is deleted from corpora within 30 days. Models trained on it are not redistributed beyond the next scheduled retraining. This is a retraining policy, not machine unlearning, whose feasibility was not assessed.
- **Provenance.** Every corpus item records its source repository and change, so withdrawal is executable.
- **Privacy.** Corpora exclude personal data: principal identities, email addresses and free-text comments. Each hosted model endpoint's clearance record states the provider's data-retention and training terms, and only endpoints whose terms forbid training on prompts are cleared above `public` by default.

## Agent-facing documentation

Crucible stays legible to agents through machine-readable documentation generated from the same sources as the code, versioned with it, and tested.

### What is published

| Artifact | Content | Served as |
| --- | --- | --- |
| API reference | Every method: purpose, JSON Schema, examples, errors, scopes, cost class | MCP tool definitions; `crucible://docs/api/{method}`; a static site |
| std reference | Every feature and type: signature with units, parameters with defaults and ranges, Checks it declares, examples, cost notes, version | `read.docs`; `crucible://docs/std/{path}@{version}` |
| Error catalog | Every error code: meaning, causes, context schema, fixes, a minimal reproducing example and its fixed version | `crucible://errors/{code}`; the `type` URI in every `ApiError` |
| Examples | Runnable Ingot examples per feature and per common task, each built in CI | `crucible://examples/{id}` |
| Skills | Role skills and task skills, such as "add a bolted joint" | Skills extension [S8] |
| Index | A short map of the docs for models, with one line per page | `crucible://docs/llms.txt` and the static site's `/llms.txt` |

**Decision D-AGT-23:** All agent-facing documentation is generated from the Rust method types, the Ingot doc comments and the error catalog, pinned to versions, and compiled in CI. Every example is built and its Checks are evaluated, and a docs page whose example fails blocks the release. `read.docs` answers for the repository's lockfile, never for the latest release. *Why:* stale docs teach agents wrong APIs; version-pinned answers match the code the agent edits. *Rejected:* hand-written agent docs (drift); retrieval over the web (unversioned, untrusted).

Docs are optimized for agents. Units are in every signature, and each page states preconditions, postconditions and failure modes. Examples are minimal, and each page fits in about 2,000 tokens (target), with links instead of inlined detail.

Anthropic found that refining tool descriptions measurably improves agent results [S31]. Crucible therefore treats doc changes as code changes and benchmarks them.

### Staying legible as Crucible grows

- **Bounded tool surface.** The MCP tool list stays under 60 tools. Growth goes into typed parameters and std features, never into new tools. A new method requires a benchmark showing gain over composing existing methods. Anthropic recommends fewer, consolidated tools [S31].
- **Namespacing.** Tool names are prefixed by group (`read_`, `inspect_`, `edit_`, `evaluate_`, `compare_`, `propose_`, `act_`, `session_`). Anthropic observed that naming choices like these have measurable effects [S31].
- **Semantic identifiers.** Responses use feature paths and instance paths, such as `gearbox/input_shaft[1]`, rather than opaque ids, with `EntityId`s alongside. Anthropic reports that readable identifiers reduce hallucination [S31].
- **Deprecations.** Every deprecated method or std feature returns a `deprecated` notice with a machine-applicable migration fix for 12 months before removal.
- **Docs coverage gate.** CI fails when any public std item lacks a doc comment, an example or units on dimensional parameters.
- **Tool-description tests.** Each release runs the golden tasks with the new docs and tool descriptions, and a drop in task success blocks the release.

## State of the art

### Lessons from existing CAD agent systems

| System | What its publisher describes | Crucible adopts | Crucible does differently |
| --- | --- | --- | --- |
| Zoo Zookeeper (announced 5 February 2026) | A conversational agent in Zoo Design Studio that writes, executes and debugs KCL; is aware of the user's selection; reviews its own changes with multi-view snapshots; has mass, volume, area and center-of-mass tools; searches docs and the web. Its roadmap includes fleets of concurrent agents and reverse engineering from STEP and STL [S11][S12]. | Code as the agent's medium; selection awareness; four-view self-review; an execute-often loop | Independent verification by Checks and a verifier, not self-review alone; Proposals with signed provenance; web results treated as untrusted |
| Autodesk Fusion MCP (May 2026) and Fusion Data MCP (July 2026) | Fusion MCP connects AI tools to a live local Fusion session. Fusion Data MCP is a cloud-hosted server for hubs, projects, folders and permissions that authenticates with the Autodesk account [S13][S14]. | A local server for the live session and a server for team data | One catalog behind both; a published permission and approval model for agent actions, which neither announcement details [S13][S14] |
| Onshape FeatureScript MCP (Onshape Labs) | AI clients generate, test and refine FeatureScript custom features, insert them into documents and run them. Once generated, the features run without further AI calls [S24]. | Agents write the platform's own feature language, so their output is ordinary, reusable code (Principle 1) | Verification by typed Checks instead of the model inspecting results; changes arrive as Proposals, not direct insertions |
| Siemens Designcenter X NX Copilot | A chat assistant inside NX that answers questions with numbered sources and links to NX commands. The pages opened describe guidance only, not actions on the model [S42][S43]. | Answers cite sources and link to methods and docs | Agents act on the design, within enforced limits |
| CloudNC CAM Assist | Generates machining strategies inside Fusion, Mastercam, NX, GibbsCAM and SolidCAM. A strategy editor lets programmers enable or suppress operations and change tools before toolpaths are made. It claims "up to 80%" of a CAM program in minutes [S15]. | Strategy first, then toolpaths; acceptance operation by operation | Strategies as Ingot in the design repository; collision and gouge Checks as gates; NC transfer as an approved Act |

### Method table

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Agent protocol | MCP 2026-07-28: stateless requests, MRTR, Tasks and Skills extensions [S1][S2][S4][S8] | Fusion MCP servers [S13][S14]; Onshape FeatureScript MCP [S24] | Adopt in full; one catalog behind every transport (D-AGT-1, D-AGT-2) | Schema conformance (O-AGT-1); golden transcripts pass on 5 MCP hosts (target) |
| Tool and response design | Consolidated, namespaced tools; concise responses; actionable errors; tool descriptions tuned against benchmarks [S31][S32] | Claude Code conventions, such as the 25,000-token response cap [S31] | At most 60 tools, a `detail` parameter, a 20,000-token cap, machine-applicable fixes | Golden-task success and tokens per success, A/B tested per release |
| Errors | RFC 9457 Problem Details [S45]; MCP tool execution errors [S3] | — | `ApiError` with typed context and ordered fixes (D-AGT-7) | Applying the first fix resolves at least 60% of errors that carry fixes (target) |
| Exactly-once mutations | Idempotency-Key semantics [S46] | — | Required keys with fingerprints, kept 24 h (D-AGT-6) | Fault injection: zero duplicate effects (O-AGT-5) |
| Delegated identity | MCP's OAuth 2.1 profile [S6]; token exchange with actor chains [S47] | — | Adopt; a downscoped token per worker | Policy-matrix oracle (O-AGT-7) |
| Prompt-injection defense | Design patterns with provable resistance [S25]; CaMeL's separation of control and data flows with capabilities, which solves 77% of AgentDojo tasks with provable security against 84% undefended [S26]; FIDES labels [S27]; the Rule of Two [S28] | CaMeL [S26] | FIDES-style labels and taint, a Plan-Then-Execute planner, Dual LLM extraction, two-phase Acts (D-AGT-18, D-AGT-20). Deviation: no CaMeL interpreter around every role. *Reason: maturity.* Design loops interleave reading results with choosing edits; Crucible bounds the damage per session through taint and keeps a CaMeL-style interpreter as a phase-3 option for tainted roles. | Injection suite: 0 attacker-chosen consequential actions (target); utility under attack within 10 points of clean utility (target) |
| Visual grounding | Set-of-Mark prompting [S36] | Zookeeper's multi-view snapshots [S11] | Set-of-Mark labels with structured mark maps, `Grid4` composites and text summaries (D-AGT-9) | Entity-selection accuracy on golden tasks at least 95% (target) |
| Design verification | CADCodeVerify's visual question loop [S17]; executable tests as in CADTests [S18] | CADCodeVerify [S17] | Checks plus an independent verifier that mutates Checks (D-AGT-12) | Planted-defect catch rate at least 90% by phase 2 (target, O-AGT-19) |
| Orchestration | Orchestrator-workers [S32]; parallel subagents scaled to task complexity [S33] | Anthropic's Research system, 90.2% better than a single agent on an internal benchmark [S33] | Validated plans, workers on branches, a merge queue; one agent by default (D-AGT-13) | Golden swarm tasks: success and cost against the single-agent baseline |
| Optimization with expensive variants | qLogNEHVI [S37][S38]; hypervolume knowledge gradient for decoupled objectives and multiple fidelities [S39]; lengthscale priors scaled with dimension [S40] | BoTorch 0.18.1 [S38] | Rust reimplementation in `std::explore` (D-AGT-15) | Hypervolume against variant count on standard test problems and golden explorations: within 5% of BoTorch at equal variant counts (target) |
| Optimization with cheap variants | NSGA-II and NSGA-III with constraints [S41] | pymoo 0.6.2 [S41] | Same methods in `std::explore` | Hypervolume against pymoo on the same problems |
| Text-to-CAD and CAD editing | Text2CAD-Bench [S16], CADPrompt [S17], CADTestBench [S18], MUSE [S19], CadEval [S44] | Best Text2CAD-Bench L1 geometric-prompt result: GPT-5.2, invalidity rate 11.1%, IoU 0.59 [S16]; the Zookeeper pages opened publish no scores [S11][S12] | Ingot agents in Check-driven loops | Adapted Text2CAD-Bench L1: invalidity rate at most 5% and IoU at least 0.75 (target; the adapted task is not directly comparable to published scores) |
| Agent reliability | pass^k [S35] | — | pass^1 and pass^4 per suite | Release gate (O-AGT-15) |
| Training data | CAD-Recode's one million procedurally generated CAD programs [S20] | CAD-Recode [S20] | An Ingot generator whose items must build and pass Checks (D-AGT-22) | Every corpus item builds; task-success gain on the held-out set |
| Provenance | in-toto Statement v1 [S48] | — | Signed `ChangeProvenance` statements | Signature and completeness oracle (O-AGT-10) |
| CAM assistance | Strategy generation with acceptance by operation [S15] | CloudNC CAM Assist [S15] | CAM programmer role gated by collision and gouge Checks; NC transfer as an approved Act | Golden CAM tasks: at least 50% of programs accepted by a programmer without edits (target) |

## Platform notes

- **Desktop, all Tier 1 OSes.** The app bundles the local MCP server as `crucible mcp` on stdio. It takes the signed-in user's credential from the OS keychain through the platform layer, as MCP directs for stdio [S6]. Local SDK connections use a Unix domain socket or a Windows named pipe, never an unauthenticated localhost port, following MCP's local-server guidance [S7].
- **Browser, Tier 1.** A browser page cannot host a stdio server. Agents in the browser use the TypeScript SDK against the team or cloud server over Streamable HTTP, and the hosted crew runs server-side. The browser app links `core/api` compiled to Wasm for the user's own edits. The browser runs no models; local models are served by a team server, so browser users have the same endpoint choices as desktop users of that deployment.
- **Servers.** `apps/mcp` and `apps/crew` ship as Linux containers for x86-64 and ARM64. Stateless MCP lets them scale behind an ordinary load balancer, and the `Mcp-Param-Repo` header routes requests to repository shards [S3].
- **Air-gapped installs.** The crew runs on local endpoints, with docs, skills and benchmark suites bundled. No external MCP servers or web access exist. Qualification runs on site.
- **Tier 2.** Tablets and phones support review, comments and Act approvals with step-up through platform authenticators. Approvers are often away from a desk, so approval works wherever viewing works.
- **Determinism.** Agent-facing renders use the deterministic CPU path. Snapshots are byte-identical within a platform class. Across classes, scene graphs and descriptions are identical, and renders agree within the perceptual threshold of O-AGT-3. CI generates Proposal snapshots on the primary platform class.
- **SDK portability.** The Python and TypeScript SDKs are pure-language clients with no native extensions, so they run wherever their runtimes run. The Rust SDK builds for every Tier 1 target, including `wasm32`.
- **Paths and text.** The API carries repository-relative, forward-slash, NFC-normalized paths on every OS, and the platform layer converts them. Ingot patches use LF line endings. Audit timestamps are server UTC and never enter evaluation.
- **GPU absence.** No agent function needs a GPU. Flux's GPU solves fall back to CPU with the cost difference reported at admission.

## Interfaces with other subsystems

### Consumed

| From | What this tab needs | Canonical types |
| --- | --- | --- |
| ING | Compiler diagnostics with machine-applicable fixes; the formatter; doc comments and feature metadata, including description templates; a string type for untrusted text (`ExternalText`, written `external("...")`); typed records for requirements in std | `Feature`, `Check`, `Quantity<D>`, `Tol<T>` |
| KLN | An Evaluation interface: demand targets, stream frames, cooperative cancellation at Op boundaries, a cost estimate before execution, priority classes, per-principal fair sharing, cache statistics; label propagation to derived artifacts | `Op`, CAS references |
| `repo` | Changes that carry `ChangeProvenance`; branches; protected branches and paths; Proposals with the fields in this tab; semantic merge that reports overlap by file, feature, parameter and entity; atomic batch insertion into the live-collaboration CRDT; releases; BOM queries; the supplier registry of verified recipients | `Proposal` |
| ANV | `EntityId` and `HistoryRecord` access; `Query` resolution with ranked candidates on failure; measurements with `ErrorBound` and witnesses; geometry diffs (volume added and removed, Hausdorff deviation); planar sections | `Body`, `EntityId`, `Query`, `ResolveError` |
| FLX | Study definitions; interactive and sign-off fidelity; error estimates; `ValidityEnvelope` flags; Field sampling with interpolation error | `Field<Domain, V>`, `ValidityEnvelope`, `Material` |
| UIX | The headless deterministic renderer with marks, Field overlays and legends; the Proposal review view; Act approval screens built from `ActionPlan` | `Body`, `Field` |
| MFG | Manufacturing Evaluations (DFM rules, CAM, removal simulation); the cost model with intervals; supplier integrations for quotes and orders; machine definitions for posting | `Part`, `Assembly` |
| MEC | Mechanical std features with doc metadata and description templates; tolerance-stack analysis for the verifier; sheet-metal and weld Checks for the DFM reviewer | `Feature`, `Check`, `Tol<T>` |
| ELX | Electronics Checks and Evaluations, so the crew can work on golden product 5 | — |
| ECO | Package signing; publication of `std::agents` and `std::explore`; license metadata for packages and datasets | Package |
| PLT | Keychain access, process sandboxing for the stdio server, OS authenticators for step-up, the telemetry pipeline | `PlatformClass` |
| The tab owning `io/` (interop) | Importers that mark all imported text as `ExternalText` with origin, and generate neutral identifiers | `Body`, `Part` |

### Provided

| To | What this tab provides |
| --- | --- |
| All tabs | The `api` method catalog and its contracts: sessions, labels, budgets, idempotency, errors, audit. UI, CLI and CI use it as agents do. |
| UIX | Proposal, review, risk and provenance data for the review view; `ActionPlan` for approval screens; presence sharing with agent sessions |
| `repo` | Provenance records, risk classes and auto-merge policy evaluation for merges |
| KLN | Admission decisions, priority classes and budget reservations for Evaluations |
| ECO | The `std::agents` package (roles, skills, exit Checks, `extract`) and the `std::explore` Wasm component |
| Every domain tab | An error-catalog and docs pipeline that each tab's errors and std packages plug into |

## Oracles

All oracles live in `oracles/agents/`, which agents can read but not write.

| Id | Verifies | Method | Phase |
| --- | --- | --- | --- |
| O-AGT-1 | MCP and schema conformance | Every tool definition validates against the MCP 2026-07-28 schema; every `structuredContent` validates against its `outputSchema`; fuzzed malformed requests yield typed errors, never crashes; an Evaluation gives identical final results through Tasks, `evaluate.get` polling and SDK streams | 0 |
| O-AGT-2 | SDK parity | Golden transcripts produce byte-identical canonical JSON through Rust, Python, TypeScript and raw MCP | 1 |
| O-AGT-3 | Observation determinism | Scene graphs, descriptions and CPU renders are byte-identical within a platform class. Across classes, graphs and descriptions are identical, and at most 0.5% of pixels differ by more than 2/255 (target). | 1 |
| O-AGT-4 | Description integrity | Every number in description text maps to a fact; perturbing a fact changes the text | 0 |
| O-AGT-5 | Idempotency | Fault injection (dropped responses, duplicate deliveries, concurrent duplicates) yields zero duplicate changes or Acts | 0 |
| O-AGT-6 | Concurrency | A TLA+ model of the change protocol is model-checked; randomized multi-writer tests show no lost updates, and stale bases are always detected | 0 |
| O-AGT-7 | Policy enforcement | A reference policy evaluator in `oracles/` must agree with the server on a generated matrix of scopes, methods, protection, taint, data classes and clearances | 0 |
| O-AGT-8 | Injection resistance | The injection suite completes zero attacker-chosen consequential actions; utility under attack is reported | 1 |
| O-AGT-9 | Act integrity | Commit without approval, a changed plan, a replayed approval or an approval from inside the delegation chain for R3 or R4 is always rejected | 1 |
| O-AGT-10 | Provenance | Every change carries a valid signed statement with complete fields; tampering is detected | 1 |
| O-AGT-11 | Budgets and rate limits | Spend never exceeds the cap by more than one Op's metering granularity; admission refuses unaffordable Evaluations; load tests show limits enforced per principal with correct `retry_after_ms` | 1 |
| O-AGT-12 | Plan validation and leases | Generated plans with cycles, overlapping concurrent write sets or missing acceptance Checks are rejected, and valid plans pass; writes from a stale lease attempt are always rejected | 2 |
| O-AGT-13 | Exploration | Hypervolume on standard test problems is within 5% of the reference implementations (target); in synchronous mode the proposal sequence is identical for equal seeds; failed variants are counted, never dropped | 1 (Bayesian), 3 (HVKG) |
| O-AGT-14 | Risk classification and auto-merge | A labeled corpus of diffs gets the expected classes; every diff that loosens a Check or tolerance is R3 or higher; auto-merge refuses every Proposal outside its policy, including tainted ones and ones with reviews from tainted sessions | 1 |
| O-AGT-15 | Agent quality gate | Golden tasks and the held-out set meet the regression thresholds per release and endpoint | 1 |
| O-AGT-16 | Docs | Every docs example builds and its Checks pass; every public std item has a doc comment, an example and units | 0 |
| O-AGT-17 | Clearance | Tripwire strings in labeled content never appear in responses to uncleared sessions | 1 |
| O-AGT-18 | Query robustness | The robustness score agrees with a labeled set of known-robust and known-fragile queries | 1 |
| O-AGT-19 | Verifier efficacy | The planted-defect catch rate meets its target | 2 |
| O-AGT-20 | Audit integrity | The hash chain verifies; any deletion or alteration is detected | 0 (chain), 1 (signed anchors) |

## Phasing

| Phase | Agent subsystem scope | Gate contribution |
| --- | --- | --- |
| 0, foundations | `core/api` types and JSON Schemas; Session, Read, Edit, `evaluate.build`, `checks`, `get` and `cancel`; idempotency; labels and taint; error catalog and docs pipeline; audit log; MCP server on stdio and HTTP; Rust SDK; source-level `inspect.describe`; policy enforcement | O-AGT-1, 4, 5, 6, 7 and 16 green; O-AGT-20 running |
| 1, wedge (golden products 1 and 2) | Inspect methods with marks, sections and overlays; `compare.diff`; Propose; CI report; risk classes; auto-merge for R0; signed provenance; the `release` Act; data classes, endpoint clearance and quarantined extraction; Python and TypeScript SDKs; roles: requirements analyst, concept designer, detail designer, simulation engineer, DFM reviewer, documentation writer, verifier; Bayesian exploration; benchmark harness with adapted Text2CAD-Bench and CADPrompt and the injection suite | Golden tasks on products 1 and 2 reach pass^1 ≥ 80% and pass^4 ≥ 60% on the best qualified endpoint (target); O-AGT-8 green |
| 2, mechanical depth (products 3 and 4) | Swarms: planner, `propose.plan`, merge queue; roles: CAM programmer, cost engineer, drawing and MBD author, catalog librarian; Act classes `send_to_supplier`, `request_quote`, `order`, `send_to_machine`, `publish_package`; MCP Apps review viewer; auto-merge for R1; held-out set of at least 200 tasks; MUSE adaptation | Swarm tasks on products 3 and 4 beat the single-agent baseline on success at no more than 3× its cost (target) |
| 3, product breadth (product 5) | Electronics-aware tasks with ELX; hypervolume knowledge gradient for decoupled, multi-fidelity exploration; customer-data opt-in program; public bounty; CaMeL-style interpreter evaluated for tainted roles | Golden tasks on product 5 at the phase 1 thresholds (target) |
| 4, full multiphysics (product 6) | Simulation engineer extended to validate models against physical test data, with correlation Checks; multiphysics explorations at scale | Drone exploration tasks find designs that pass sign-off Checks (target: at least 3 Pareto-optimal variants confirmed at sign-off fidelity) |
| 5 and later (proposed) | A compliance-evidence role that assembles certification evidence from Checks and provenance; agents across organizations, if A2A is adopted after review | Defined per domain |

## Open questions

1. **Model attestation for external hosts.** Changes made through external hosts are marked `Declared`. Could signed provider receipts let Crucible attest the model identity?
2. **Export control with hosted models.** Can a hosted model endpoint meet the ITAR end-to-end encryption carve-out, given that the provider decrypts prompts [S50]? Legal counsel must answer this before any `export_controlled` clearance is granted to a hosted endpoint.
3. **R1 thresholds.** Are a 90% margin floor, 0.5 mm deviation and 1% cost increase the right auto-merge limits? Phase 1 review data should set them.
4. **ABC filtering.** Can per-document license filtering of ABC (date and LICENSE tab) be done reliably enough to use any of it [S22][S23]?
5. **Asynchronous exploration.** Is the throughput gain worth giving up a reproducible proposal sequence by default?
6. **Host support for MCP extensions.** Will major hosts support Tasks and Skills by phase 1? Polling and Prompts fallbacks exist; their effect on agent success is unmeasured.
7. **Quarantine independence.** Must the quarantine endpoint come from a different provider than the privileged agent, or is a separate tool-free call enough?
8. **Mutation testing on large assemblies.** What sampling strategy keeps verifier cost bounded on assemblies of 1,000 or more parts?
9. **Tokens spent in external hosts.** These are invisible to Crucible. Should budgets include declared token usage from hosts, which cannot be verified?
10. **Agent-to-agent protocols across organizations.** Should supplier agents interact through A2A 1.0 [S51] or only through shared Proposals?

## Contract change requests

1. **Add Session and Act to the API method groups.** Section 7 names six groups: Read, Edit, Evaluate, Inspect, Compare and Propose. *Reason:* MCP 2026-07-28 requires explicit server-minted handles for state, which needs a Session group. Irreversible real-world effects need their own permission and approval semantics, and folding them into Propose would blur reversible design changes with irreversible effects.
2. **Add "Evaluation" to the glossary**, meaning a request to Kiln to demand Op results, with a lifecycle and a report. Ops are the cached nodes; an Evaluation is the request. *Reason:* the API, Kiln, CI and the UI all need one name for a running build, check or simulation request; without it each tab invents one, such as "job" or "run".
3. **Avoid "operation catalog" for `api`.** The overview and briefs should say "API method" for entries in the `api` catalog. *Reason:* the glossary reserves Operation for Anvil and Flux primitives.
4. **Extend section 5 with `Labels` and `DataClass`.** Every artifact in CAS and every API response carries an integrity label and a data class, propagated by Kiln. *Reason:* export control, confidentiality and taint must survive derivation, so they must be core types, not agent-specific ones.
5. **Extend `Proposal` in section 5** with author, delegation chain, parent and plan, risk class, labels, snapshots and provenance, as specified in this tab. *Reason:* agent work and human review both need these fields, and `repo` owns the storage.
6. **Ask ING for an `ExternalText` type**, written `external("...")`, which importers use for untrusted text. *Reason:* importers must mark untrusted text at the type level so that labels survive into source.

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
