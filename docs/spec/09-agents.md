# Agents (AGT)

Agents use the same typed `api` as people: one catalog of methods in eight groups, served over MCP 2026-07-28, native SDKs and WIT. Agents edit only branches and deliver Proposals that build, meet every check's gate, carry signed provenance and survive an independent verifier. The server, not the model, enforces safety: labels on every context, no authority for untrusted text, and human approval of every outside effect's exact plan.

## Scope and invariants

This tab owns the `api` crate (catalog, sessions, boundary labels, budgets, errors, audit payloads, Acts) and `apps/mcp`, `apps/crew` and `apps/model-gateway`. It also specifies observation, roles, swarms, Proposals, benchmarks and training data. Kiln, `repo`, Anvil, Flux and PLT own the machinery underneath.

1. **Parity of capability.** People, agents, the UI, the CLI and CI call the same methods; only accountable humans approve Acts, protected merges and policy.
2. **Branch confinement.** Agents write only to unprotected branches; protected branches change only through Proposals.
3. **Proposals are the unit of agent work.** A Proposal enters review only after it builds, meets every check's gate and carries server-generated snapshots.
4. **Enforcement lives in the server.** `api` checks scopes, budgets, labels and approvals on every call, whatever model or host drives the agent.
5. **No correctness depends on a model.** Every agent output becomes Ingot source or a typed record that deterministic checks verify.
6. **Every claim has an oracle.** Exit criteria are checks, and graders live in `oracles/agents/`, which agents can read but never write.

| Term | Meaning |
| --- | --- |
| Session | A server-minted handle binding a principal, a branch, a grant, a budget and a model context |
| Model context | The unit that accumulates a label (contract section 7.6): a hosted-crew conversation, or an external host's (user, client identity) pair |
| Role | An Ingot record plus a skill: purpose, scopes, write-set rule, exit checks and outputs |
| Delegation grant | A signed, time-bound grant from a human to agents: scopes, repository, budget, expiry |
| Risk class | R0 to R4, computed by the server from a Proposal's semantic diff and its authoring contexts' labels |

"Evaluation" always means a Kiln request, so measuring agents is called benchmarking. Phase 0 serves the catalog in single-principal mode, a local install with one human. Scopes, labels, grants and approvals arrive with KLN's identity and authorization in phase 1.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Parity of capability | Every UI, CLI, CI and agent action is an API method; tool lists differ only by grant | A missing method fails the catalog coverage test | AGT-O-2 | 0 |
| Branch confinement | Agent sessions open only on unprotected branches | `session/branch_protected` | AGT-O-7 | 1 |
| Server-side enforcement | Scopes, labels, budgets and approvals on every call; single-principal mode before | Typed `auth`, `label` and `budget` errors | AGT-O-7 | 1 |
| Checked outputs | Agent output lands as Ingot or typed records that checks verify | `edit/introduces_errors`, `propose/preconditions_failed` | AGT-O-15 | 1 |

## The `api` surface

### One catalog, several transports

**Decision D-AGT-1:** The `api` method catalog is the only programmatic surface of Crucible. MCP tools, SDK methods, WIT functions, UI commands and CLI subcommands map one-to-one onto API methods. *Why:* agents are first-class users, a second surface would drift from the first, and principle 1 forbids privileged paths. *Rejected:* a separate agent API (drifts and doubles testing); a code-only surface that runs scripts (loses typed inspection, evaluation and review). (revised in round 3)

`core/api` has no transport code; the desktop app, web app and CLI link it in process. `apps/mcp` serves it over stdio and Streamable HTTP on the official Rust SDK, `rmcp`, which implements 2026-07-28 and 2025-11-25 [S10]. The hosted crew (`apps/crew`) uses only the public SDK, and `apps/model-gateway` carries attested clients' model traffic (D-AGT-19), both from phase 2.

### MCP profile

MCP 2026-07-28 removes protocol sessions, so requests carry their version and capabilities in `_meta` and stateful servers mint explicit handles [S1][S2][S3]. It adds Multi Round-Trip Requests (MRTR), moves Tasks into an extension, and deprecates Roots, Sampling and Logging [S2].

**Decision D-AGT-2:** Crucible targets MCP 2026-07-28 with Tasks and Skills, and serves 2025-11-25 for twelve months after phase 1. It needs neither extension, since clients can poll `evaluate.get` and read skills as resources. *Why:* stateless requests scale without sticky sessions, deprecations get at least twelve months [S2], and host support is outside Crucible's control. *Rejected:* a custom protocol (no host ecosystem); building on 2025-11-25 (session affinity); requiring the extensions. (revised in round 3)

| MCP element | Crucible use |
| --- | --- |
| `server/discover` | Versions, extensions, catalog version; instructions state D-AGT-25 [S2][S4][S8] |
| `tools/list` | One tool per granted method, in deterministic order; varies by authorization only [S3] |
| `tools/call` | `outputSchema` and `structuredContent` on every tool; domain failures as tool execution errors [S3] |
| Resources | Change-addressed `crucible://` URIs with long `ttlMs` and `cacheScope: "private"` [S2] |
| `subscriptions/listen` | Branch-head, Proposal and Evaluation resources and `toolsListChanged` [S2] |
| Tasks extension | Long Evaluations return tasks, driven by `tasks/get`, `tasks/update` and `tasks/cancel` [S4] |
| MRTR | `act.commit` returns `act/approval_pending` with a request id, never a URL (D-AGT-20); step-up uses `insufficient_scope` [S5][S6] |
| Skills extension | Role skills with SHA-256 manifests, implemented in `apps/mcp`, since `rmcp` does not list Skills [S8][S10] |
| Apps extension | A read-only Proposal viewer (phase 2) that never approves anything [S9] |
| HTTP headers | Gateways rate-limit on `Mcp-Method` and `Mcp-Name`; `x-mcp-header` mirrors only `shard_key` [S3] |
| Not used | Sampling, Roots, Logging and HTTP+SSE [S2] |

Mirrored headers are visible to intermediaries [S3], so `shard_key` is an HMAC-SHA-256 of the repository id under the tenant's routing key, truncated to 16 bytes. `requestState` is sealed with AEAD and bound to the principal, the request digest and a 15-minute expiry [S5]. `edit.apply` becomes the tool `edit_apply`, because the Claude API allows only letters, digits, `_` and `-` in tool names [S63].

Hosts must treat tool annotations and skill content as untrusted [S3][S8], so trust in approved role skills binds only the hosted crew.

### Sessions, identity and delegation

A principal is a person (`user:<id>`), an agent instance (`agent:<org>/<role>/<instance>`) or a service (`service:<name>`); an agent always acts for a human. The delegation chain runs from the delegating human (index 0) to the current actor. The server derives it from its own session lineage, never from token `act` claims, which RFC 8693 makes informational for nested actors [S47].

Remote transports use MCP's OAuth 2.1 profile with Client ID Metadata Documents, audience-bound tokens and step-up through `insufficient_scope` [S2][S6].

**Decision D-AGT-3:** A Session is an opaque 128-bit random handle bound to the principal and token issuer, expiring by default after 24 hours idle or 7 days. Atomicity is per Change and isolation per branch, with no long-lived transaction. *Why:* MCP recommends explicit handles [S3], a handle never authenticates [S7], and cheap branches already isolate work. *Rejected:* protocol-level sessions (removed from MCP); multi-call transactions with locks (contention, leaked locks, a second concept beside branches).

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
    pub context: Labels,                 // the model context's label (D-AGT-24)
}
```

The effective grant intersects the human's permissions, the role's scopes, repository policy and the request. Clearance is the meet of the human's, the client's or endpoint's (D-AGT-19) and the policy's.

**Decision D-AGT-28:** Agents act under delegation grants, signed and time-bound, naming scopes, repository, budget and expiry. Per-tenant crew instances exchange tokens only against a live grant, only for agent scopes, sender-constrained by DPoP or mTLS, and never for Approvals or `policy:admin`. *Why:* otherwise one compromise of `apps/crew` yields authority over every delegating user (R5-45), and DPoP binds tokens to the client's key [S58]. *Rejected:* standing token exchange; bearer tokens for crew workers.

Only the delegating human steers a running agent (`session.control`); anyone else's @mention becomes a request in that human's inbox, with attachments as `ExternalText`.

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

`EditsApplied` returns the new `ChangeId`, any rebase, the formatted `SourcePatch`es, diagnostics, a semantic diff summary and usage.

**Decision D-AGT-4:** Structured edits are a convenience layer that lowers to Ingot source patches; the formatter normalizes touched regions, and the response returns the patch. *Why:* one model, three editors; reviewers and agents read the same Ingot whatever produced it. *Rejected:* edits on geometry or on an opaque feature tree (nothing exists only outside Ingot).

Compile errors fail with `edit/introduces_errors` unless `allow_errors` is set on the agent's own branch. Stale patches fail with `edit/patch_mismatch`, and edits outside the write set with `edit/write_set_violation`.

**Decision D-AGT-5:** Concurrency control is optimistic: every mutating call names its base Change. On a stale base the server rebases, and reports it, only when `repo`'s semantic merge finds no overlapping file, feature, parameter or entity. *Why:* explicit over magic; agents need to know their view was stale. *Rejected:* pessimistic locks (deadlocks, locks abandoned by crashed agents); silent rebase (hides semantic interference).

A call, a Proposal merge and a swarm's parent merge are each one Change. On a live branch (phase 2) an agent's Change enters the CRDT as one batch.

### Idempotency and retries

MCP 2026-07-28 removed stream resumability, so clients re-issue requests lost with a broken stream [S2], and a retried mutation must not apply twice.

**Decision D-AGT-6:** Every method that changes state or spends budget requires an idempotency key, a client-generated 128-bit random value. The server keeps (principal, method, key) with a SHA-256 fingerprint of the canonical arguments and the response for 24 hours. *Why:* exactly-once effects under routine retries. *Rejected:* deduplication by argument hash (merges legitimately repeated calls); transport resumability (removed from MCP).

| Situation | Behavior |
| --- | --- |
| Same key and fingerprint, completed | The stored response, marked `replayed: true` |
| Same key and fingerprint, running | `request/in_flight` with `retry_after_ms` |
| Same key, different fingerprint | `request/idempotency_mismatch`, naming the original call |
| Key older than 24 hours | Treated as new, with a notice |

The SDKs generate keys and retry with the same key under capped, jittered exponential backoff.

### Evaluations and streaming results

Builds, checks, simulations, manufacturing plans, costing and explorations run as Evaluations. Their states map to MCP task states: `queued` and `running` to `working`, `done` to `completed`, `aborted` to `cancelled` or `failed` [S4].

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

Every Evaluation ends in an `EvaluationReport`. A long one returns a task when the client declared Tasks, and otherwise waits up to `wait_ms` and returns an id for `evaluate.get` [S4]. Cancellation is an Abort (contract section 7.2), and the final frame lists what completed.

### Drag streams

Direct manipulation needs results every frame without a Change per pointer move. `evaluate.subscribe { targets, overrides, ceiling }` opens a result stream under literal overrides keyed by ING's `LiteralSite`. `edit.stream` sends override updates to it and ends in exactly one `edit.apply` that writes the final literals, or in a discard.

Kiln keys overridden nodes by their overrides, never shares those results (KLN, ING-O-12) and runs them on PLT's `Interactive` pool lane. UIX's drag preview, MEC's sketch drag and ELX's router use this pair.

### Budgets, limits and admission

AGT defines `Budget` and `PriorityClass`, which live in `base`; PLT adopts `Usage` as its resource record.

```rust
pub struct Budget {
    pub money: Option<Money>,            // base Money { amount: Decimal, currency }
    pub core_seconds: Option<u64>,
    pub gpu_seconds: Option<u64>,
    pub model_tokens: Option<u64>,       // measured calls only (D-AGT-34)
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

Budgets nest from organization to session. Default ceilings are 25 USD per session, 200 USD per Proposal tree and 1,000 USD per day, and raising one is audited.

**Decision D-AGT-29:** Admission reserves the priced upper bound of each Evaluation's work, never a mean. An Op estimated above 10 core-seconds gets a deterministic work budget from the remaining money and reaches a safe point every 10 core-seconds; exhaustion aborts it at its last checkpoint. *Why:* solves, certified geometry and Wasm components vary in cost by orders of magnitude at one input size (R6-29). *Rejected:* regression estimates as reservations; caps only between Ops, which an unbounded factorization overruns.

The work budget never enters an `OpKey`: an Op completes with its usual value or aborts and writes nothing. GPU seconds come from timestamp queries on compute-only submissions. A failed reservation returns `budget/exceeded` with cheaper options. Sessions are warned at 80% of a cap, and spending three times the role's median raises an alert.

| Method class | Default sustained rate | Burst |
| --- | --- | --- |
| Read, Inspect except snapshots | 50 per second | 200 |
| `inspect.render`, `inspect.section`, `inspect.ask_render` | 4 concurrent | — |
| Edit (`edit.stream` updates count once per second) | 10 per second | 30 |
| Starting Evaluations | 5 per second | 20 |
| Propose | 1 per second | 10 |
| `act.prepare` | 10 per hour; at most 3 pending approval requests | — |

Limits are per principal at the gateway (HTTP 429 or `limit/rate` with a retry delay). Concise detail, the default, uses about a third of the tokens [S31]. Results above 20,000 tokens are truncated with a cursor, below Claude Code's 25,000-token limit [S31].

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
    pub context: serde_json::Value,      // schema in the error catalog
}
```

**Decision D-AGT-7:** Every failure is an `ApiError` shaped like RFC 9457 Problem Details, with typed context and ordered fixes, returned as an MCP tool execution error. Codes are written `<family>/<code>`, a namespace apart from method names. *Why:* RFC 9457 is the standard format [S45], models self-correct from tool execution errors [S3], and dotted codes like `propose.policy_unsatisfied` read as methods (R9-47). *Rejected:* free-text errors; JSON-RPC errors, from which models recover poorly [S3]; method-shaped codes. (revised in round 3)

Diagnostics and `ResolveError`s arrive in `context` with their own fixes. A fix from third-party code carries `data_untrusted` and may not touch dependencies, checks, tolerances, policy or protected paths. Families name failures, never method groups.

| Family | Representative codes | Typical fix |
| --- | --- | --- |
| `auth` | `scope_denied`, `step_up_required`, `no_live_grant`, `human_only`, `break_glass_forbidden` | Step-up; ask the delegating human for a grant |
| `session` | `expired`, `branch_protected`, `lease_lost` | Open a session; fork a branch |
| `edit` | `stale_base`, `patch_mismatch`, `introduces_errors`, `write_set_violation`, `protected_path`, `override_site_unknown` | Re-read and retry; apply the compiler's fix |
| `query` | `resolve_failed`, `no_robust_candidate` | Pin a candidate; `inspect.suggest_query` |
| `budget`, `limit` | `exceeded`, `rate` | Lower fidelity; wait |
| `propose` | `preconditions_failed`, `policy_unsatisfied`, `self_review_forbidden`, `check_protected` | The failing checks and missing approvals |
| `act` | `approval_pending`, `plan_changed`, `subject_mismatch`, `recipient_unverified`, `onsite_required`, `denied_cooldown` | Wait for the assigned approver; prepare again |
| `label` | `write_down`, `exceeds_clearance`, `client_unattested`, `raw_external_forbidden` | A new context; a cleared endpoint; a declassification |

### Native SDKs and WIT

Rust types in `core/api` are the single source of truth. A build step emits JSON Schema 2020-12 [S2] and generates the MCP tools, the WIT package and the SDKs. Rust ships in phase 0, Python in phase 1 and TypeScript in phase 2 (contract section 13.2), with byte-identical canonical JSON through each.

`crucible:api` serves UIX's `panel` world and ECO's tool and connector worlds, never evaluation worlds. It has one interface per group, each function returning `result<T, api-error>`, and stays at `@0.1.0` until it freezes after contract section 13.1's name clearance. Calls run under the session's grant narrowed by the component's (D-ECO-27), and strings follow D-AGT-18.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| MCP server | 2026-07-28; Tasks and Skills used, neither required; 2025-11-25 for twelve months after phase 1 | Unsupported version returns the supported list | AGT-O-1 | 0 |
| Skills serving | `skills/list`, `skills/get` and manifests in `apps/mcp`; resources otherwise | Manifest mismatch refuses the skill | AGT-O-1 | 1 |
| Sessions and delegation | Handle bound to principal and issuer; chain from server lineage | `session/expired`, `auth/scope_denied` | AGT-O-7 | 0 (single principal), 1 |
| Delegation grants | Crew token exchange only against a live grant; DPoP or mTLS | `auth/no_live_grant` | AGT-O-24 | 2 |
| Structured edits | Lower to `SourcePatch`; atomic per call; handle-cited values | `edit/*` errors with fixes | AGT-O-6 | 0 |
| Optimistic concurrency | Exact base; rebase only when disjoint | `edit/stale_base` | AGT-O-6 | 0 |
| Idempotency | Keys with fingerprints kept 24 h | `request/idempotency_mismatch` | AGT-O-5 | 0 |
| Evaluation streams | Frames over Tasks, polling and SDK streams; identical final results | Abort lists completed nodes | AGT-O-1 | 0 |
| Drag streams | `evaluate.subscribe` under `LiteralSite` overrides; `edit.stream` ends in one `edit.apply`; never shared-cached | `edit/override_site_unknown` | AGT-O-6 | 1 |
| Admission and metering | Priced upper-bound reservations; safe points every 10 core-seconds | `budget/exceeded`; budget Abort keeps the checkpoint | AGT-O-11 | 1 |
| Rate limits | Per principal at the gateway | `limit/rate` | AGT-O-11 | 0 |
| Errors | RFC 9457 shape, `<family>/<code>`, typed context, ordered fixes | Third-party fixes labelled and restricted | AGT-O-1 | 0 |
| SDKs | Generated from one schema | Schema drift fails the build | AGT-O-2 | 0 (Rust), 1 (Python), 2 (TypeScript) |
| WIT package `crucible:api` | One interface per group, generated from the Rust types; `@0.1.0` until the freeze | A version mismatch refuses instantiation | AGT-O-2 | 1 |
## Method catalog

Every method is `<group>.<name>` in contract section 7.6's eight groups, which ECO's and KLN's methods join. A breaking change creates a version such as `edit.apply@2`, and the old one is served for at least twelve months [S2].

Methods marked † change state or spend budget, so they need an idempotency key and, except `session.open`, a session.

Read and Inspect methods accept a `ChangeRef`, and every result carries its labels. Strings from nodes of untrusted integrity are `ExternalText` handles (D-AGT-18). Approvals are not methods: assigned humans give them on the approval page (D-AGT-20).

Sessions emit the events `session.called` (method, status, audit entry, usage), `session.asked`, `session.answered`, `session.controlled` and `session.closed`. They carry ids and states only (D-KLN-34), and UIX's agent panel reads them.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| `session.open` † | `SessionOpen` → `SessionOpened` | `auth/scope_denied`, `session/branch_protected`, `label/exceeds_clearance` | AGT-O-7 | 0 |
| `session.status` | Handle → head, grant, context label, usage, open Evaluations and questions | `session/expired` | AGT-O-1 | 0 |
| `session.ask` † | A typed question with an answer schema → the delegating human's answer as typed data; one blocking question per session | `session/question_expired` | AGT-O-7 | 1 |
| `session.close` † | Handle → final usage; unused budget returned | `session/unknown` | AGT-O-11 | 0 |
| `session.reset_context` † | A human resets an external host's context label with WebAuthn after clearing its conversation; audited (D-AGT-24) | `auth/human_only` | AGT-O-17 | 1 |
| `session.control` † | Pause, resume or steer a hosted-crew session; delegating human only | `auth/not_delegator` | AGT-O-7 | 2 |
| `session.presence` † | Share selection or camera with an agent session; delegating human only | `auth/not_delegator` | AGT-O-7 | 2 |
| `read.tree` | Path → entries with kind, size, hash and labels | `read/not_found` | AGT-O-1 | 0 |
| `read.source` | Path, range → text with free-text spans as handles (D-AGT-18) | `read/not_found`, `label/exceeds_clearance` | AGT-O-8 | 0 |
| `read.outline` | Path or feature → calls, parameters, checks, spans | `build/parse_failed` (partial outline) | AGT-O-1 | 0 |
| `read.history` | Branch → Changes with provenance; messages as handles | `read/not_found` | AGT-O-10 | 0 |
| `read.branches` | Repository → name, head, protection, owner | — | AGT-O-1 | 0 |
| `read.symbols` | Query → path, kind, signature, doc URI | — | AGT-O-16 | 1 |
| `read.language_service` | An LSP 3.17 request (completion, hover, inlay hints, semantic tokens, code actions) at a Change → ING's result | `read/request_unsupported` | AGT-O-1 | 1 |
| `read.docs` | Symbol, error code or URI → `DocEntry`s pinned to the lockfile | `docs/not_found` with nearest matches | AGT-O-16 | 0 (errors), 1 (std) |
| `read.external_text` | Handle → typed extract, or raw text where D-AGT-25 allows | `label/raw_external_forbidden` | AGT-O-8 | 0 (handles), 2 (extracts) |
| `read.value` | `ValueRef` → typed value; marks the context `data_untrusted` | `read/unknown_handle` | AGT-O-17 | 1 |
| `read.bom`, `read.where_used` | KLN's EBOM, then MBOM, service BOM and where-used | `read/not_found` | AGT-O-1 | 1 (EBOM), 2 |
| `read.catalog` | Filters → catalog part summaries | `catalog/filter_invalid` | AGT-O-1 | 2 |
| `read.coverage` | Domain, scale, level, status → COV's coverage map rows and limit records | Unbacked rows show `Planned (phase n)` (COV) | AGT-O-1 | 0 |
| `read.packages`, `read.package`, `read.registry_bundle` | ECO registry search, package metadata and signed offline bundles | `package/not_found` with nearest names; `package/unavailable` (bundles) | AGT-O-1 | 1 (`read.package`), 2 |
| `read.events` | Source, cursor → events in sequence order | `events/cursor_expired` | AGT-O-1 | 1 |
| `read.subscribe`, `read.unsubscribe` | A webhook subscription with thin payloads (ECO); `maintainer` or `admin` people only | `events/url_refused` | AGT-O-22 | 1 |
| `read.machine_data` | Machine → state and as-run records from MFG's gateway | `mfg/gateway_unreachable` | AGT-O-1 | 2 |
| `read.audit` | Filter → audit entries; needs `audit:read` | `auth/scope_denied` | AGT-O-20 | 1 |
| `inspect.scene` | Root, depth, include → `SceneGraph` | `build/failed` (partial graph), `inspect/too_large` (cursor) | AGT-O-3 | 1 |
| `inspect.entity` | Entity → kind, surface type, size, adjacency, provenance chain | `inspect/entity_gone` with `HistoryRecord`s | AGT-O-3 | 1 |
| `inspect.query` | Ingot query → entities with notes; `stability: true` adds ANV's sampled analysis | `query/resolve_failed` with candidates | AGT-O-18 | 1 |
| `inspect.suggest_query` | Entities → robust queries with sampled stability scores | `query/no_robust_candidate` | AGT-O-18 | 1 |
| `inspect.measure` | Distance, angle, clearance, thickness, mass, interference → `Quantity`, `ErrorBound`, witnesses | `inspect/kind_unsupported` | AGT-O-3 | 1 |
| `inspect.render` | `RenderRequest` → `Rendered` snapshot from `apps/headless-render` | `render/too_many_marks` | AGT-O-3 | 1 |
| `inspect.ask_render` | `std::agents` template, marks → mark ids, booleans or counts as `ValueRef`s (D-AGT-26) | `render/template_unknown` | AGT-O-8 | 2 |
| `inspect.section` | Plane → curves, SVG, legend | `inspect/empty_section` with the nearest offset | AGT-O-3 | 1 |
| `inspect.field` | Points, region, statistics or extrema → values with error and zones | `field/out_of_domain` | AGT-O-3 | 1 |
| `inspect.describe` | Target, detail → `Description` | `build/failed` (describes what built) | AGT-O-4 | 0 |
| `edit.apply` † | `ApplyEdits` → `EditsApplied` | `edit/*`, `label/write_down` | AGT-O-6 | 0 |
| `edit.stream` † | Override updates to a subscription; ends in one `edit.apply` or a discard | `edit/override_site_unknown` | AGT-O-6 | 1 |
| `edit.revert` † | Changes → a forward Change | `edit/revert_conflict` | AGT-O-6 | 0 |
| `edit.undo` † | One repository transaction from KLN's log; own branches only | `edit/not_owner` | AGT-O-6 | 0 |
| `edit.create_branch`, `edit.reset_branch` † | Create an own branch; reset an own unprotected branch | `edit/branch_exists`, `edit/branch_protected` | AGT-O-6 | 0 |
| `edit.import_archive` † | ECO archive → a new design repository; spans untrusted unless an organization device key signed them (KLN) | `archive/incomplete` listing missing objects | AGT-O-1 | 1 |
| `edit.grant_capability`, `edit.revoke_capability` † | A Wasm component capability grant or revocation in `ingot.lock` (ECO) | `policy/denied` naming the rule | AGT-O-7 | 1 |
| `evaluate.build` † | Targets, `Fidelity`, `estimate_only` → `EvaluationReport` | `budget/exceeded`, `build/failed` | AGT-O-11 | 0 |
| `evaluate.checks` † | Selection, `Fidelity` → `CheckOutcome`s | As above | AGT-O-1 | 0 |
| `evaluate.subscribe` † | Targets, overrides, fidelity ceiling → a frame stream on Kiln's drag lane | `budget/exceeded` | AGT-O-1 | 1 |
| `evaluate.simulate` † | Study, `Fidelity` → Fields with `ErrorBudget`s and zones | `flux/study_invalid`; zones flag, never hide | AGT-O-1 | 1 |
| `evaluate.manufacture` † | Setup → toolpaths, collisions, removal, cycle time | `mfg/setup_invalid` | AGT-O-1 | 2 |
| `evaluate.cost` † | Quantity, process → cost lines with intervals and price sources | `cost/unpriced_lines` (partial report) | AGT-O-1 | 1 |
| `evaluate.ci` † | Change → the `CiReport` that Proposal CI would produce | — | AGT-O-14 | 1 |
| `evaluate.explore`, `evaluate.materialize` † | Exploration → Pareto frames; a variant → `SetParameter` edits | `explore/no_feasible_point`, `explore/variant_unknown` | AGT-O-13 | 2 |
| `evaluate.get` | Evaluation, `after_frame`, `wait_ms` ≤ 25,000 → status, frames | `evaluation/unknown` | AGT-O-1 | 0 |
| `evaluate.cancel` † | Evaluation → status; cancellation is an Abort | — | AGT-O-1 | 0 |
| `compare.diff` | From, to, levels → `SemanticDiff`, optional overlay | `compare/unrelated` (flagged) | AGT-O-14 | 1 |
| `compare.merge_preview` | Base, left, right → KLN's conflicts and result, nothing written | — | AGT-O-6 | 1 |
| `compare.resolve` | Manifest, lockfile → a new lockfile and its diff, not applied (ECO) | `package/unsatisfiable` with the explanation | AGT-O-1 | 1 |
| `propose.create`, `propose.update` † | Title, rationale, target, parent, draft, ready → `Proposal` | `propose/preconditions_failed`, `propose/closed` | AGT-O-14 | 1 |
| `propose.get`, `propose.list` | Proposals, with free text as handles | — | AGT-O-8 | 1 |
| `propose.review` † | Verdict, findings → KLN's `ReviewVerdict` | `propose/self_review_forbidden` | AGT-O-7 | 1 |
| `propose.comment` † | Anchor, body → `Comment`; @mentions of agents become inbox requests | — | AGT-O-7 | 1 |
| `propose.merge`, `propose.withdraw` † | Expected head → merged Change; or a reason | `propose/policy_unsatisfied`, `propose/conflict` | AGT-O-14 | 1 |
| `propose.endorse_text` † | Spans → a signed endorsement by a `maintainer` or `approver` outside their authoring chain (D-AGT-18) | `auth/human_only`, `auth/in_authoring_chain` | AGT-O-8 | 1 |
| `propose.waive` † | A Waiver (contract section 2) that an authorized human signs on the approval page; KLN stores it | `auth/human_only`, `propose/check_protected` | AGT-O-9 | 1 |
| `propose.policy` † | A Proposal to policy files; humans merge, two of them for D-KLN-41 items | `label/untrusted_context`, `auth/human_only` | AGT-O-7 | 1 |
| `propose.declassify` † | A declassification record for two signers, one an export officer; KLN stores it | `auth/human_only` | AGT-O-17 | 1 |
| `propose.plan` † | Plan → validated plan and work-item states | `plan/invalid` | AGT-O-12 | 2 |
| `propose.change_request`, `propose.change_order` † | KLN lifecycle records; change orders approved through their release plan | `propose/preconditions_failed` | AGT-O-9 | 2 |
| `propose.purge` † | KLN purge request for two administrators | `auth/human_only` | AGT-O-7 | 2 |
| `act.prepare` † | Class, payload → `ActPlan` with digest | `act/recipient_unverified`, `label/exceeds_clearance` | AGT-O-9 | 1 |
| `act.commit` † | Plan digest → `act/approval_pending { request }` until approved, then `ActReceipt` | `act/plan_changed`, `act/subject_mismatch`, `act/denied`, `act/onsite_required` | AGT-O-9 | 1 |
| `act.status` | Plan digest → state, approvals, receipt | — | AGT-O-9 | 1 |

## Observation interfaces

Agents perceive designs through a scene graph, geometry queries, snapshots, descriptions and semantic diffs. Every channel answers from the same Kiln results with `ErrorBound`s, and a text-only model receives the same facts as a vision model.

### Structured scene graph

`inspect.scene` returns the evaluated product of one Change as a typed tree, never from UI state.

A `SceneNode` carries its instance path (`gearbox/input_shaft[1]`), kind, item, producing feature and span, placement, material and representation. It adds bounds and mass properties with `ErrorBound`s, verdict counts, Fields and children. Identical siblings collapse with a count, and failed builds return partial graphs.

### Geometry queries

- `inspect.query` evaluates a query such as `part.faces(normal: +z, area: 100mm2..)` and returns entities with `Merged`, `Partial`, `FragileAnchor` or `NearTie` notes, or a `ResolveError`.
- `inspect.entity` returns type, size, adjacency and provenance from `HistoryRecord`s.
- `inspect.measure` returns a `Quantity` with an `ErrorBound` and witness points.
- `inspect.suggest_query` turns entities picked from a snapshot into queries that keep resolving to them.

**Decision D-AGT-8:** Agents select geometry only through `Query` expressions and `EntityId`s, and `inspect.suggest_query` ranks candidates by ANV's sampled stability analysis, reporting `RankSwap { at }` with its sample. The score is `Sampled` evidence, never a guarantee. *Why:* resolution certifies only the evaluated configuration (contract section 5), while rank selectors flip inside ranges like the bracket's `width` (R2-22, R8-02). *Rejected:* indices or screen coordinates; the first query that resolves; ±10% sampling alone; sampled scores presented as guarantees. (revised in round 3)

The score is the fraction of sampled configurations that resolve to the same lineage. Agents submit queries scoring 1.0 unless the rationale states a deviation. The CI report carries the protected-branch stability results (contract section 5).

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
    pub instruction_capable: bool,       // D-AGT-26
    pub visible_summary: Description,    // from typed facts; untrusted names as handles
}
```

The server resolves each request to a UIX `ViewState`, so a Snapshot is a `ViewState` under a `RenderProfile` (contract 2).

Marks follow Set-of-Mark prompting [S36], and each label maps to an `EntityId`, so "fillet the edges marked 3 and 7" resolves exactly. `Grid4` returns four views in one image, as Zookeeper's self-review uses [S11].

**Decision D-AGT-9:** `inspect.render` dispatches to `apps/headless-render`, which links UIX's renderer, so `api` depends on neither. Snapshots key on a `RenderProfile`, return marks, legend and extrema as data, and stay `Unverified`, outside every `OpKey`, compared by ꟻLIP [S62]. *Why:* rasterizers generate code per host CPU [S61], so bytes differ across the class (R6-26); profiles change legends (R3-35); core crates never link apps (R9-25). *Rejected:* canonical CPU renders; images without structured side data; rendering inside `api`. (revised in round 3)

Byte identity holds only on one pinned CI renderer image. Proposals and benchmarks use the review profile (`en`, SI with millimetres, light theme). Proposal snapshots are stored once as Assets, so every reviewer sees the same bytes.

**Decision D-AGT-26:** A snapshot or section SVG is instruction-capable when imported appearance or any visible Body, text or overlay derives from an untrusted node. A clean context asks about one only through `inspect.ask_render`, a quarantined vision call on a versioned `std::agents` template, whose `ValueRef` answers set `data_untrusted`. *Why:* embossed letters, part names, notes and textures can carry instructions (R5-17, R11-02), and answers computed from attacker-chosen pixels can still steer an edit (R11-36). *Rejected:* trusting every snapshot; tainting every snapshot with a merged supplier part; trusted `ask_render` answers. (revised in round 3)

The scene graph, measurements and descriptions stay non-tainting, because every string they take from an untrusted node is a handle.

### Sections and descriptions

`inspect.section` returns curves with the cut-plane `ErrorBound`, an SVG hatched per material and an optional overlay. An empty cut returns the nearest offset that meets material.

`inspect.describe` renders typed facts through templates, without a model. It returns `text`, `facts` (each number with source and bound) and a `detail` level of `Brief` (80 words), `Standard` (400) or `Full`. The canonical bracket, brief:

> Part `bracket` (item 100-0042), aluminium 6061-T6. Bounding box 60.0 × 40.0 × 24.0 mm; mass 39.2 g ± 0.1 g. Features: sketch, extrude 4 mm, rib 20 mm, fillet 2 mm on 2 edges. Checks: 1 of 1 provisional `Pass` at `Interactive`, conditional on model form. Regularized peak von Mises stress away from the clamp and loaded face: 112 MPa ± 20 MPa (`Estimated`) against 144 MPa, margin 8% at the bound.

**Decision D-AGT-10:** Canonical descriptions come from typed facts and templates, with no model text, and only the canonical form is stored, diffed and reviewed. Std and `crucible::` phrasing is trusted; a third-party template's phrasing is an `ExternalText` handle. *Why:* descriptions feed reviews and benchmarks, so every number must trace to a fact, and publisher verification establishes identity, not safe text (R5-13). *Rejected:* model-written canonical descriptions; trusting verified publishers' templates. (revised in round 2)

### Semantic diffs

`compare.diff` explains what changed between two Changes:

| Level | Content |
| --- | --- |
| Source | Formatted Ingot text diff, free text as handles |
| Features | Features added, removed, moved; parameters old → new with units |
| Checks | Verdict and margin changes; checks added, removed or loosened; `#[waive]` requests |
| Geometry | Volume added and removed, Hausdorff deviation with `ErrorBound` (Anvil) |
| Metrics | Mass, cost, regularized peaks, cycle time and declared objectives, with intervals |
| BOM | Lines added or removed, quantity changes, new catalog parts |
| Policy | Checks, tolerances, oracle references, protected paths, lockfile pins, recipient records |

The overlay shows added and removed material in a colour-blind-safe pair over ghosted geometry. A policy-level diff sets `policy_sensitive: true` for risk classification.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Scene graph and measurements | Typed tree from Kiln results; `Quantity` with `ErrorBound` and witnesses | Partial graph with diagnostics | AGT-O-3 | 1 |
| Geometry queries | `Query` and `EntityId` only; `NearTie` and other notes surfaced | `query/resolve_failed` with ranked candidates | AGT-O-18 | 1 |
| Query robustness ranking | ANV's sampled stability analysis; `RankSwap` with its sample; `Sampled`, never a guarantee | `query/no_robust_candidate` | AGT-O-18 | 1 |
| Snapshots and overlays | `apps/headless-render`; `RenderProfile` in the key; `Unverified` class; ꟻLIP comparison; legends as data | `render/too_many_marks` | AGT-O-3 | 1 |
| Instruction-capable images | Neutral appearance; quarantined `inspect.ask_render` answering with `ValueRef`s | Reading one directly sets `instruction_tainted` | AGT-O-8 | 2 |
| Sections | Curves with bounds, SVG, overlay | `inspect/empty_section` with nearest offset | AGT-O-3 | 1 |
| Descriptions | Template-generated; every number a fact; third-party phrasing as handles | Describes what built | AGT-O-4 | 0 (source facts), 1 (evaluated facts) |
| Semantic diffs | Seven levels; `policy_sensitive` flag | `compare/unrelated` flagged | AGT-O-14 | 1 |
## Roles

A role is a `Role` record in a package: scopes, a write-set rule, an external-text policy (never, or extracts), exit checks, outputs and model requirements. Its skill lives at `skill://crucible/<role>/SKILL.md` with a manifest digest. The crew is the roles in the open-source `std::agents`, and anyone can publish one.

**Decision D-AGT-11:** Roles are data plus instructions in an open package. Their exit criteria are checks in `std::agents::exit`, which CI evaluates over the typed `std::agents::proposal` view. *Why:* "no privileged code" applies to agents too, and exit criteria must be machine-checkable to be oracles. *Rejected:* roles hard-coded in the runtime (privileged and opaque); prose-only exit criteria (not enforceable). (revised in round 2)

A role skill changes only through a reviewed, benchmarked Proposal. The hosted crew loads another publisher's role only after `policy:admin` approves its version and digest.

### Scopes

Scopes are the units of permission in grants, tokens and roles; there is no wildcard, and hosts request scopes by step-up [S7].

| Scope | Grants |
| --- | --- |
| `design:read` | Read, Inspect and Compare methods, except `read.external_text`, `read.value` and `read.audit` |
| `external:read` | `read.external_text` and `read.value`, under D-AGT-25 |
| `design:edit` | Edit methods on the session's branch, within its write set |
| `eval:build`, `eval:simulate[:fidelity]`, `eval:manufacture`, `eval:cost`, `eval:explore` | The matching Evaluate methods, simulation up to the stated fidelity |
| `propose:author`, `propose:review`, `propose:merge`, `propose:plan` | Authoring; review outside one's own lineage; merge under policy; plans and child sessions |
| `act:<class>` | `act.prepare` and `act.commit` for one Act class; commit waits for an assigned human |
| `audit:read` | `read.audit` |
| `policy:admin` | Policy, protection, clearances, recipients and auto-merge; humans only, never by token exchange |

### Role catalog

Every role holds `design:read` and `propose:author`; the verifier and DFM reviewer add `propose:review`, and the planner `propose:plan` and `propose:merge` on its integration branch.

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

Phase 1 ships contract section 13.2's three roles from external MCP hosts; the CAM programmer arrives with CAM in phase 2 (R4-12). A value a role cannot source, such as a tolerance or a price, becomes a finding for a human, never an invention.

Reviewers never edit what they review, and catalog librarian Proposals always carry `data_untrusted`. A CAM program is offered to a human step by step, as CloudNC's CAM Assist offers strategies [S15].

### Planner

The planner turns a goal into a validated plan, dispatches work items and assembles the parent Proposal, never editing design source. It never reads external text, so its actions are fixed before untrusted data is processed (Plan-Then-Execute [S25]). An item that exhausts its attempts gets one re-plan, then goes to the delegating human with its failure history.

### Independent verifier

The verifier runs in a fresh context with no session lineage shared with the author, on another model family where policy requires. Its typed view holds requirements, the IR, the semantic diff, check outcomes, the CI report and the rationale's typed fields, never the author's free text.

Every review attacks uncovered requirements, worst-case tolerance stacks, omitted load cases, material extremes, query fragility, CI replay in another class and manufacturability. Check mutation thins walls by 50%, removes fillets, doubles loads and swaps in the weakest permitted material. A check surviving every mutation is flagged possibly vacuous, and findings carry an Ingot test that fails on the head.

**Decision D-AGT-12:** Every agent Proposal faces a verifier that shares no lineage with the author, sees no author free text and runs a fixed attack catalog with check mutation. Its review is `Attested` only under a different delegating human, in the hosted crew or behind the gateway; a `Declared` review needs a human approval too. *Why:* self-review shares blind spots, author text is an injection channel (R5-02), and Crucible cannot see one host play both roles (R11-12). *Rejected:* self-verification ([S12]); render questions only (CADCodeVerify's 7.30% point-cloud improvement [S17] misses checks that cannot fail); server lineage alone. (revised in round 3)

Mutation covers the changed Parts and the checks their dependency closure reaches. Beyond the verifier's budget a fixed hash rule samples them, and the report states the count.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Role packages | `Role` records with skills and manifest digests in `std::agents` | Unapproved manifest refuses the role in the hosted crew | AGT-O-1 | 1 |
| Scopes | No wildcard; incremental step-up; `policy:admin` human-only | `auth/scope_denied` | AGT-O-7 | 1 |
| Exit checks | `std::agents::exit` over the typed Proposal view | `propose/preconditions_failed` | AGT-O-15 | 1 |
| Phase 1 roles | Detail designer, simulation engineer, verifier | `session/role_unavailable` | AGT-O-15 | 1 |
| Further roles | The nine others in the catalog | `session/role_unavailable` | AGT-O-15 | 2 |
| Independent verifier | Typed view; attack catalog; scoped mutation; `Attested` or `Declared` | Merge blocked until a verifier review exists at head | AGT-O-19 | 1 |

## Orchestration of swarms

A swarm is a tree of Proposals: a plan, child Proposals on workers' branches, a merge queue and a verifier before the target.

### When to use a swarm

Multi-agent systems use about 15× the tokens of chat and suit heavily parallel work, while coding parallelizes less well [S33]. Design work is closer to coding.

**Decision D-AGT-13:** The default is a single agent, and a swarm starts only when a validated plan has at least two items that can run in parallel. Default caps are 8 parallel workers per Proposal tree and a delegation depth of 2. *Why:* cost outgrows benefit when work is not parallel, and Anthropic saw 50 subagents spawned for simple queries [S33]. *Rejected:* always-on swarms (cost, merge churn); unbounded recursive delegation (cost and blurred accountability).

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

A `Plan` holds the goal, items, integration branch, a budget from the parent Proposal and `max_parallel` (default 8). `propose.plan` checks acyclicity, disjoint concurrent write sets, acceptance checks, budgets and qualified endpoints, or fails with `plan/invalid`. A valid plan creates the integration branch.

Contract section 13.2's build-program work item maps onto it: crate to write set, capability row to requirement, oracle ids to acceptance, held-out split to `held_out`.

### Execution

[[DIAGRAM diagrams/09-agents-swarm-flow.jsx: swarm flow · planner, parallel workers, merge queue, two verifiers]]

Read it top to bottom, then along the bottom row. Solid arrows carry changes, dashed arrows send Evaluations to Kiln on the right, and the left column shows the budget at each level.

1. **Dispatch.** Each ready item is leased, up to `max_parallel`, to a child session on a branch forked from the integration head.
2. **Work.** The worker reads, edits, builds, checks and inspects, then proposes into the integration branch.
3. **Light verification.** A verifier checks each child for uncovered requirements, check mutation and query fragility.
4. **Merge queue.** Children merge in dependency order with CI on each result, so the integration head meets the gate predicate.
5. **Assembly and review.** The parent Proposal targets the branch, the verifier runs the full catalog, and review follows.

A lease lasts 10 minutes and any call renews it; an expired lease returns the item to `Pending`, and stale writes fail with `session/lease_lost`. Plan state lives on the parent Proposal, so the crew resumes after a restart.

### Coordination without messages

**Decision D-AGT-14:** Agents never message each other directly; plans, work items, Proposals, reviews and anchored comments written through the API are the only medium. Agents in two organizations cooperate only through shared Proposals under `share_external` and standing releases (D-AGT-33). *Why:* coordination stays versioned, audited and visible, spoofed messages are a named risk (ASI07 [S30]), and A2A messages are free text outside labels [S51]. *Rejected:* direct messaging, including A2A 1.0; a shared scratch memory (poisonable, ASI06 [S30]). (revised in round 3)

Another agent's comment arrives as an `ExternalText` handle, so agents exchange facts through typed failure reports, findings with tests and check outcomes.

### Conflict resolution

| Stage | Outcome |
| --- | --- |
| Prevention | Concurrent items have disjoint write sets; overlapping ones run in sequence |
| Semantic conflict | A conflict on a feature, parameter, entity or net returns the item to its worker as typed input |
| Behavioural conflict | Children pass alone but the merge fails a check: a reconcile item gets both diffs and the failing check |
| Alternatives | Competing passing solutions are ranked by the plan's objectives; a tie goes to a human |
| Exhaustion | One re-plan, then the delegating human sees both alternatives with failure histories |

### Design-space exploration

`evaluate.explore` searches a parametric space for trade-offs through Kiln and Flux. Variants are parameter assignments in a CAS record, not branches. A request names variables, objectives with units, constraints (default: every `Error`-severity check), a fidelity ladder, strategy, batch size, budget and seed.

| Situation | Strategy |
| --- | --- |
| Initial design | Scrambled Sobol sequence of 2(d + 1) points |
| Expensive variants (under about 500 affordable, up to about 50 variables) | Bayesian optimization: qLogNEHVI, or qLogNoisyExpectedImprovement for one objective [S37][S38]; dimension-scaled lengthscale priors [S40] |
| Cheap variants or mostly categorical spaces | NSGA-II for two objectives, NSGA-III for more [S41] |
| Several fidelities or separable objectives (phase 3) | Hypervolume knowledge gradient [S39] |

**Decision D-AGT-15:** Exploration strategies are Rust in the Wasm component package `std::explore`, with BoTorch and pymoo as references, not dependencies. Rounds are synchronous by default, and asynchronous batches are an opt-in that marks the record non-reproducible. *Why:* Python and PyTorch cannot run deterministically in the sandbox, on every OS or in browsers, and reproducible records outweigh asynchronous throughput. *Rejected:* a BoTorch sidecar (no browser, no determinism); evolutionary methods only, though each variant costs a Flux solve and Bayesian optimization targets costly functions [S66]. (revised in round 3)

- **Failures** keep their typed errors, and a Gaussian-process classifier weights acquisition by build success.
- **Validity.** `Invalid` or `Extrapolated` results leave the Pareto front by default.
- **Fidelity ladder.** Screening runs at `Interactive` and the top five rerun at `SignOff`; disjoint enclosures flag `fidelity_disagreement`.
- **Determinism.** Seeds are inputs, and Gaussian processes fit by deterministic L-BFGS from fixed Sobol restarts.

### Scheduling on Kiln workers

Kiln owns Op scheduling; this tab owns admission and accounting. Every Evaluation carries a `PriorityClass`:

| Class | Used by | Preemption |
| --- | --- | --- |
| `Interactive` | Sessions where a human is waiting, drag streams included | Only by drags, at node boundaries (KLN) |
| `Agent` | Agent sessions | By `Interactive`, at node boundaries (KLN) |
| `Ci` | Proposal CI and merge queues | By `Interactive` |
| `Batch` | Explorations and benchmarks | By all; resumes from cached Ops |

Within a class, admission shares capacity by Dominant Resource Fairness, which equalizes each principal's largest share of any resource [S65]. Planner and verifier may use the strongest qualified endpoint and workers a cheaper one. Anthropic's Opus 4 lead with Sonnet 4 subagents beat one Opus 4 agent by 90.2% [S33], which golden tasks test.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Plans and validation | Acyclic, disjoint concurrent write sets, acceptance checks, budgets; held-out grading | `plan/invalid` with fixes | AGT-O-12 | 2 |
| Leases and fencing | 10-minute leases; attempt numbers fence stale writers | `session/lease_lost` | AGT-O-12 | 2 |
| Merge queue | Children merge in dependency order with CI per merge | Conflicts return to the worker as typed input | AGT-O-12 | 2 |
| Exploration | `std::explore`: Sobol, NSGA-II and III, Bayesian optimization; deterministic in synchronous mode | `explore/no_feasible_point`; failures counted | AGT-O-13 | 2 |
| Multi-fidelity exploration | Hypervolume knowledge gradient | Falls back to single-fidelity search, reported | AGT-O-13 | 3 |
| Priority classes | Four classes with preemption at node boundaries (KLN); Dominant Resource Fairness within a class | — | AGT-O-11 | 0 |
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
    pub snapshots: Vec<ObjectId>,        // server-generated at head, review profile
    pub risk: RiskAssessment,            // class and the diff items that set it
    pub labels: Labels,                  // join of every authoring context's label
    pub reviews: Vec<ReviewVerdict>,
    pub state: ProposalState,            // Draft | Open { ready } | Merged | Withdrawn | Superseded
    pub usage: Usage,
}
```

`Rationale` holds a summary, requirement ids, design choices with evidence ids, deviations and limitations. Before a non-draft `propose.create`, the server checks:

1. The head builds at each target's declared fidelity.
2. Every check meets the gate predicate (contract section 5); `#[waive]` counts only with a matching Waiver record, which agents never sign.
3. Snapshots exist at the head: a `Grid4` of each changed Part or Assembly, a geometry-overlay diff and an overlay per changed study.
4. The rationale has a summary and, where requirements exist, a requirement link.
5. Every Change on the branch carries complete provenance.

A failure returns `propose/preconditions_failed` with fixes. Drafts skip items 1 to 3 and cannot be merged.

### CI report

`service:ci` writes the `CiReport` on untrusted-evaluation workers (contract section 7.8), and `evaluate.ci` shows agents the same report in advance. It names the Change, lockfile digest and evidence watermark, and holds each CI Evaluation's `EvaluationReport`. Those give outcomes per class, deltas, zone flags, query stability, oracle integrity and usage, and trusted builders recompute what releases need after merge.

### Risk classification

| Class | Meaning | Examples |
| --- | --- | --- |
| R0 | No semantic change | Formatting and comments with an identical IR hash; regenerated snapshots |
| R1 | Contained design change | Parameters within declared ranges on unreleased designs; no check, tolerance, BOM or dependency change; no margin below 90% of its target-head value; every authoring context clean |
| R2 | Ordinary design change | New features, checks, studies or materials; BOM changes; dependency updates keeping behavior versions; any R1-shaped change from a `data_untrusted` context, every `Declared` host included |
| R3 | Sensitive change | Checks or tolerances loosened; `#[waive]` requests; oracle references; protected paths; behavior-version bumps; change orders; any change from an `instruction_tainted` context |
| R4 | Critical | Changes feeding an Act class (a release candidate, a posted program, files bound for a supplier); policy files; recipient records |

**Decision D-AGT-16:** Risk class is a deterministic function of the semantic diff, the target and every authoring context's integrity flags. Loosening, waiver requests and `instruction_tainted` content are at least R3, and `data_untrusted` content, any `Declared` host included (D-AGT-34), at least R2. *Why:* loosening a check is the cheapest reward hack, and untrusted typed values steer edits without text (R5-01). *Rejected:* model-assessed risk; one class for all agent work (review fatigue, ASI09 [S30]); calling unseen host context clean (R11-12). (revised in round 3)

Merged catalog and supplier parts raise nothing, because a merge clears integrity on typed inputs (contract section 5). A flag that never cleared would put every real assembly at R2 (R9-04, R11-13).

### Human review and separation of duties

For agent Proposals, UIX's Proposal view adds provenance, the risk class and its reasons, integrity flags with sources, the verifier report and the canonical description. Findings anchor to `EntityId`s, feature paths or spans and return to the author as typed input.

- No principal in the delegation chain may approve the Proposal, except the delegating human for R0 to R2.
- R3 and R4 need a human outside the chain; repository policy can require more.
- Agent reviews never count toward human approval requirements.
- Approvals need a credential enrolled for approval, and Crucible's phone clients offer none (contract section 7.6).

### Auto-merge

Auto-merge is a repository policy, off by default, changed only by two humans (D-KLN-41).

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

**Decision D-AGT-17:** Auto-merge applies only to R0 and R1 Proposals whose authoring contexts were all clean, which only hosted-crew and gateway-attested contexts can be. It also needs an `Attested` verifier review, CI in two classes meeting the gate and an unvetoed quiet period; R2 and above need a human. *Why:* low-risk changes should not queue behind people, behavior changes need accountability (R5-01), and an unseen host context is not clean (R11-12). *Rejected:* auto-merge on "all checks pass" (checks can be incomplete); never auto-merging (review fatigue); auto-merge for external hosts. (revised in round 3)

`service:merge` performs auto-merges, never the author, recording the policy version. An agent freeze stops auto-merge, new agent sessions and agent writes within 5 seconds (target).

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
    pub client: ClientInfo,                      // client identity; declared tool inventory
    pub context: Labels,
    pub inputs: Vec<ReadRecord>,                 // digests of what the context read
    pub transcript: Option<ObjectId>,            // hosted crew always; other hosts if uploaded
}
```

Each record is an in-toto Statement v1 with the Change digest as `subject` [S48], signed by the deployment's provenance key. The model is attested only when the crew or gateway made the call, and otherwise `Declared`. Instructions and transcripts keep the context's label and their own retention (D-AGT-32).

### Reversibility

| Effect | Undone by |
| --- | --- |
| Change on an agent's own branch | `edit.reset_branch`, `edit.undo` or `edit.revert` |
| Merge, swarm result or auto-merge | `edit.revert` as a forward Change in a Proposal; a daily digest lists auto-merges |
| Release | Not undoable; superseded by a change order and a new release |
| Compensable or revocable Act | Cancellation or revocation, recorded as a new Act |
| Irreversible Act | Not undoable, hence approval of the exact plan |

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Proposal records | Fields above; labels joined from authoring contexts | `propose/closed` | AGT-O-14 | 1 |
| Preconditions | Build, gate predicate on every check, snapshots, rationale, provenance | `propose/preconditions_failed` with fixes | AGT-O-14 | 1 |
| CI report | `service:ci` on untrusted-evaluation workers; per-Proposal namespace; one `EvaluationReport` per Evaluation | Agents cannot write it | AGT-O-14 | 1 |
| Risk classes | Deterministic from diff, target and integrity flags; `Declared` hosts at least R2 | — | AGT-O-14 | 1 |
| Separation of duties | Chain from server lineage; R3 and R4 need a human outside it | `propose/self_review_forbidden` | AGT-O-7 | 1 |
| Auto-merge | R0 and R1 from clean attested contexts; `Attested` verifier; two classes; quiet period | `propose/policy_unsatisfied` | AGT-O-14 | 2 |
| Agent freeze | All agent writes stop within 5 s (target) | — | AGT-O-7 | 1 |
| Provenance | Signed in-toto statements for every Change | Unsigned Change refused | AGT-O-10 | 1 |

## Labels and injection defence

Prompt injection is unsolved: Meta calls it "a fundamental, unsolved weakness in all LLMs" [S28], and OWASP ranks it first [S29]. Crucible relies on no model resisting it: authority comes only from principals and grants, every value carries `Labels`, and the server enforces every boundary.

| Threat (OWASP agentic risk [S30]) | Primary controls |
| --- | --- |
| Instructions in imports, comments, strings or textures (ASI01) | Four instruction sources (D-AGT-18); handles; labels; extraction |
| Misuse of a legitimate method (ASI02) | Scopes, write sets, risk classes, Act approvals |
| Stolen or escalated credentials (ASI03) | Sender-constrained tokens; delegation grants (D-AGT-28) |
| Malicious servers, skills or packages (ASI04) | Approved skill manifests; signed packages; stdio MCP servers only in PLT's sandbox |
| Code execution (ASI05) | Only Ingot and determinized Wasm components; Proposal CI in single-use microVMs |
| Poisoned memory, spoofed messages (ASI06, ASI07) | No shared agent memory; no direct messaging (D-AGT-14) |
| Cascading failures (ASI08) | Budgets, attempt limits, merge-queue CI, freeze |
| Over-trust by reviewers (ASI09) | Risk classes, verifier reports, server-generated approval pages |
| Rogue agents and exfiltration (ASI10) | Write-down, clearances, egress only through Acts, audit |

### Instruction authority and untrusted content

**Decision D-AGT-18:** Instruction authority has four sources: the delegating human's goal, approved role skills, first-party documentation from the hermetic builder, and spans endorsed in the same repository. Everything else returns as an `ExternalText` or `ValueRef` handle, including every string from an untrusted node. *Why:* provable defences constrain an agent after untrusted input [S25]; endorsement by merge once trusted injected comments (R5-02), and agent literals came back as part names (R11-02). *Rejected:* classifiers or spotlighting as primary controls (kept as signals); trusting verified publishers or protected branches; returning endorsed spans raw without listing them (R11-37). (revised in round 3)

Untrusted origins are imported files, supplier, catalog and web content, third-party package text, extraction output and attachments. Merging the Change that introduced a pin, Asset or span clears both flags on its typed values, never its free text (contract section 5). A merged supplier STEP file thus yields trusted geometry and untrusted names, while unmerged submissions and `read.value` handles stay `data_untrusted`.

Such strings include scene names, BOM text, check names, quoted diagnostics, CI reports, diffs and description facts. `repo` records each span's integrity as this server witnessed it (KLN). A span returns as a handle when its author is outside the reader's chain or it is untrusted.

A span becomes trusted only through `propose.endorse_text`. A `maintainer` or `approver` outside its authoring chain sees it verbatim, hidden characters highlighted, and signs over its bytes. Importers keep original names as `external(...)` values, never endorsed.

### Context labels and write-down

**Decision D-AGT-24:** Every model context carries the join of the `Labels` of every value returned to it, and every write carries that label. An external host's context is a server-stored (user, client identity) pair that every token family, grant and stdio launch joins, and write-down compares confidentiality only. *Why:* a context is a derivation path Kiln never sees (R5-01), and a reconnecting host must not get a clean label (R11-04). *Rejected:* labelling only Kiln derivations; non-tainting typed values; labels per token family or workspace; integrity that blocks writes (R11-01). (revised in round 3)

The hosted crew's context is its conversation. Reading an `ExternalText` handle's content or an instruction-capable image sets `instruction_tainted`, and any untrusted value sets `data_untrusted`; trusted text never taints (R11-35). A write down fails with `label/write_down` unless a declassification names it. Only `session.reset_context`, confirmed by the human with WebAuthn after clearing the host conversation, resets a label.

### Taint and the Rule of Two

Meta's Rule of Two: an agent should hold at most two of untrusted input, sensitive access, and the power to change state or communicate [S28].

| Context | Edit own branch | Propose | Merge or auto-merge | Prepare Acts |
| --- | --- | --- | --- | --- |
| Clean (hosted crew or gateway-attested only) | Yes | Yes | Subject to policy | Yes |
| `data_untrusted` | Yes | Yes; at least R2 | No auto-merge | Yes; the plan carries the flag |
| `instruction_tainted` | Yes | Yes; at least R3 | No | Yes; the approval page lists the taint sources |

An `instruction_tainted` context holds all three narrowly. It changes only its own branches, Proposals humans review and Acts humans approve, which is the supervision the rule asks for [S28] (R5-30).

### Quarantined extraction and external hosts

Roles that need facts from untrusted documents use the Dual LLM pattern [S25], as FIDES does [S27]. `std::agents::extract` runs a model with no tools and no other context that fills a templated Ingot record, schema-validated, range-checked and `data_untrusted`. It ships in phase 2; until then external text is handles only.

**Decision D-AGT-25:** Outside the hosted crew, `read.external_text` returns only quarantined typed extracts. Raw reads need the per-client flag `allow_raw_external`, set by two humans, recording the declared tool inventory and refused above `internal`. *Why:* a host with its own fetch or mail tools completes the lethal trifecta outside Crucible's sight (R5-07). *Rejected:* clearance at the response alone; trusting hosts' sandboxes; a mandatory second provider for the extractor. (revised in round 3)

The extractor may share the role's provider, since isolation comes from no tools, no shared context and a separate API project with retention off. A second provider would add a sub-processor, not isolation. Crew web fetches return extracts, and no URL is built from context data.

**Decision D-AGT-34:** A host outside the model gateway is `Declared`: its model, tool inventory and token counts are recorded as stated and never trusted. Its contexts start `data_untrusted`, and it becomes `Attested` only through the gateway or signed per-call provider receipts. *Why:* its model may have read a poisoned page or another server's output first (R11-12), and an unverifiable count cannot bound spend. *Rejected:* "clean as far as Crucible saw"; budgets on declared tokens; trusting self-reported inventories.

`server/discover` states D-AGT-25 in the server instructions.

### Write sets, protected paths and two-person rules

Write sets confine edits to globs, and protected branches (`main`, `release/*` and any policy names) reject direct writes. Protected paths (`oracles/**`, policy files, behavior-version pins, recipient records) take agent writes only through Proposals at R3 or R4.

**Decision D-AGT-27:** `api` enforces KLN's one two-person list (D-KLN-41), which includes this tab's items: client and endpoint clearance, standing releases, `allow_raw_external` and training opt-in. Under break-glass `api` serves only reads, freeze, ref revert, lock release and session termination, refusing the rest with `auth/break_glass_forbidden`. *Why:* one phished administrator could otherwise export an ITAR programme in one action (R5-15), two lists drifted (R11-22), and unbounded break-glass voids the rule (R11-15). *Rejected:* single-administrator control; a second list here; no break-glass. (revised in round 3)

Policy Proposals from a context with either integrity flag are refused.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Instruction authority | Four sources; untrusted strings in every response as handles | Injected instructions change no consequential action | AGT-O-8 | 1 |
| Free-text handles and endorsement | Span-level integrity; signed endorsement from outside the authoring chain | `auth/human_only`, `auth/in_authoring_chain` | AGT-O-8 | 1 |
| Context labels and write-down | Join of returned values; (user, client identity) for hosts; write-down on confidentiality | `label/write_down` | AGT-O-17 | 1 |
| Context reset | `session.reset_context`, human with WebAuthn, audited | `auth/human_only` | AGT-O-17 | 1 |
| Quarantined extraction | Tool-free, templated, schema-validated, isolated project | Invalid output dropped and reported | AGT-O-8 | 2 |
| External-host raw reads | Extracts only; `allow_raw_external` at `internal` or below | `label/raw_external_forbidden` | AGT-O-8 | 1 |
| `Declared` hosts | Contexts start `data_untrusted`; declared tokens recorded, never enforced | — | AGT-O-14 | 1 |
| Protected paths | Agent writes only through Proposals; R3 or R4 | `edit/protected_path` | AGT-O-7 | 1 |
| Two-person rules | KLN's list enforced at `api`; bounded break-glass | `propose/policy_unsatisfied`, `auth/break_glass_forbidden` | AGT-O-7 | 1 |
## Clearance, egress and data protection

### Endpoint and client clearance

**Decision D-AGT-19:** Every model endpoint and external client carries a clearance, a confidentiality bound granted under D-KLN-41. Clearance above `internal` needs the hosted crew or an attested client behind `apps/model-gateway`, and `controls` clear only inside the organization's boundary or under a `ControlAuthorization`. *Why:* metadata documents cannot stop localhost impersonation [S55] or show where a host forwards content (R5-08), and a hosted model decrypts prompts, which the ITAR carve-out forbids third parties [S52] (R11-26). *Rejected:* clearance by metadata document; host filtering; model redaction; counsel ruling per endpoint rather than once on the template. (revised in round 3)

A context receives only values that it and its human both clear. An attested client is pre-registered, authenticates with `private_key_jwt` [S59] from a hardware key, and routes model traffic through the gateway, which enforces the allowlist and records the model. A `ControlAuthorization` for a provider uses the regulated cloud's basis (US persons, US regions), never an encryption carve-out.

`Declared` endpoints never clear above `internal` or any `controls`, and an unattested client asking for more gets `label/client_unattested`. The crew and gateway arrive in phase 2, so phase 1 agent contexts stay at `internal` or below.

Crucible provides mechanisms, and the organization decides what is lawful; classified information is out of scope (contract section 13.1).

The EAR carve-out needs end-to-end encryption with FIPS 140-2 or successor modules and no intentional storage in a Country Group D:5 country [S49]. The ITAR carve-out needs unclassified data, FIPS 140-2 or AES-128 strength, no §126.1 country and an authorized recipient [S50][S52]. No third party may hold the means of decryption [S52]. An ITAR release includes exchanges with foreign persons [S53], so an endpoint is a recipient.

### Exfiltration channels

| Channel | Control |
| --- | --- |
| Uncleared endpoint or client | Clearance at the response (D-AGT-19) |
| Lower-labelled repository | Write-down (D-AGT-24) |
| Bytes leaving the tenant | `release_data` (D-AGT-30) |
| An external host's own tools | Extracts only (D-AGT-25) |
| URLs in agent output | Inert text unless allowlisted; external images never load in review |
| Hosted crew runtime | Egress only to the API, cleared endpoints and quarantined fetches |
| Read volume | Bytes per context against the role baseline; alert, optional freeze |

### Audit and personal data

KLN owns the audit log, its envelope and its rule of ids and digests, never labelled content (D-KLN-30). AGT owns each entry's `api`-call payload: chain, session, method, argument digest, status, labels, cost, client and trace. Act plans, approvals and policy changes are separate labelled CAS records the entry names by `ObjectId`.

**Decision D-AGT-32:** Provenance, transcripts and API logs follow KLN's pseudonymous ids, crypto-shreddable identities and retention locks, each lock carrying the customer's `retention_basis` (D-KLN-43). Transcripts and API logs keep 12 months by default, apart from release records. *Why:* GDPR Article 17(3)(b) covers only Union or Member State law, and 17(3)(e) legal claims [S56], so a US duty needs its own basis (R11-42). *Rejected:* names in entries; one seven-year retention; a second rule here, since two owners drift (R9-29). (revised in round 3)

Agent presence and per-person analytics have a works-council mode, since German law gives works councils co-determination over monitoring devices [S57]. Crucible ships records-of-processing entries, an impact assessment template and its model sub-processors with regions and retention.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Endpoint and client clearance | Confidentiality bounds granted by two humans | `label/exceeds_clearance` naming a cleared endpoint | AGT-O-17 | 1 |
| Attested clients and model gateway | `private_key_jwt` from a hardware key; gateway records the model | `label/client_unattested` | AGT-O-17 | 2 |
| Control defaults | `controls` only to in-boundary endpoints or under a `ControlAuthorization` | `label/exceeds_clearance` | AGT-O-17 | 1 |
| Egress monitoring | Read-volume baselines per role | Alert; optional freeze | AGT-O-8 | 2 |
| Audit payload | `api`-call fields inside KLN's entries; labelled records by `ObjectId` | Missing entry fails the call | AGT-O-20 | 1 |
| Personal data | KLN's pseudonymous ids and retention locks; 12-month transcripts | A lock blocks shredding with its basis recorded | AGT-O-20 | 2 |

## Acts and approvals

Every effect outside Crucible is a two-phase Act (contract section 2) whose class declares family, plan schema and reversibility.

| Act class | Family | Effect | Reversibility | Phase |
| --- | --- | --- | --- | --- |
| `release` | Record | Signed release tag, with deliveries to internal systems | Superseded by a change order | 1 |
| `grant_deviation` | Record | A deviation against a release | Revocable going forward | 2 |
| `yank_package`, `deprecate_package` | Record | Registry status | Yank never deletes | 2 |
| `send_to_supplier` | Data release | Files for quotation or production | Irreversible | 1 |
| `export` | Data release | Repository archive, release bundle, Git mirror | Irreversible | 1 (archive, bundle), 2 (Git mirror) |
| `request_quote`, `order` | Data release | RFQs and purchase orders | Orders compensable | 2 |
| `share_external`, `notify_external` | Data release | Sharing with another organization; outside messages | Access revocable | 2 |
| `standing_release` | Data release | Bounded recurring transfers on one channel (D-AGT-33) | Revocable going forward | 2 |
| `publish_package` | Data release | A public registry version | Yankable | 2 |
| `publish_passport` | Data release | A digital product passport (MFG) | Superseded | 3 |
| `send_to_machine` | Physical effect | A program or recipe of an MFG kind, through the machine gateway | Irreversible once run | 2 |
| `store_machine_job` | Physical effect | OPC UA job `Store` only | Revocable before start | 3 |
| `send_print_job`, `start_print` | Physical effect | A print job; a restricted start | Cancellable | 2 |
| `send_robot_program` | Physical effect | A robot program file into the program store | Irreversible once run | 2 |
| `flash_device` | Physical effect | A Software item image to a named board, read back, target held | Irreversible once released | 3 |
| `run_rig_test` | Physical effect | A test on a rig under an `unattended_safe` policy | Irreversible | 2 |

**Decision D-AGT-20:** `act.prepare` yields a deterministic `ActPlan` whose digest is the approval subject, and `act.commit` returns only a request id to the model. Named approvers decide on one server page on its own origin and WebAuthn relying party [S60], with an enrolled credential (contract section 7.6). *Why:* a URL reaching a model can be forwarded to a busy approver (R5-04, [S54]), and script injected on the main origin could start a ceremony (R11-05). *Rejected:* URL or form elicitation in the host; approval by any authority holder; open-ended pre-approvals; approval on the main origin. (revised in round 3)

The approval origin serves only server text under `default-src 'none'` with scripts by hash, and issues challenges only to itself (`SameSite=Strict`, no CORS). Its challenge hashes plan digest, request id and approver id.

Native clients open it in a browser session bound to the request id (`ASWebAuthenticationSession` on Apple platforms, the default browser elsewhere), returning by a `crucible://` callback. Apps use passkeys only for associated domains [S68], so every client, Crucible's cloud included, approves in this browser session, which PLT's `Authenticator` opens (D-PLT-41).

```rust
pub struct ActPlan {
    pub digest: Sha256,                  // over the canonical plan; the approval subject
    pub class: ActClass,
    pub effects: Vec<Effect>,            // one Approval covers every effect (contract 7.6)
    pub recipients: Vec<RecipientId>,    // KLN RecipientRecords, internal systems included
    pub subject: Option<ObjectId>,       // release: ApprovalSubject; program: posted text and evidence
    pub device: Option<DeviceTarget>,    // class, serial, location, program number, what it replaces
    pub authorization: Option<ControlAuthorizationId>,
    pub standing: Option<StandingReleaseId>, // a transfer under D-AGT-33
    pub labels: Labels,                  // payload joined with the preparing context
    pub requested_by: Vec<PrincipalId>,
    pub expires: Timestamp,              // default 24 h
}
```

The page shows contract section 7.6's contents, physical-effect section included, plus integrity flags and a banner for recipient records changed within 7 days. `act.prepare` rejects the characters contract section 7.6 forbids (`act/payload_rejected`), and a plan changed after approval fails with `act/plan_changed`. Approvals are single-use, except that a release Approval covers operator pulls of the released program at qualified serials of its class (contract section 7.6).

A release plan's digest covers the `ApprovalSubject`'s `ObjectId`, the tag and the effectivity, never the `ChangeId` or CI report. The subject holds every affected Item's `ItemDefinition` digest (contract section 5), so swapped firmware, Material versions or documents void the approval. `act.commit` recomputes it and refuses a mismatch with `act/subject_mismatch`. A rebase that keeps the subject keeps its approvals, which are also the change order's (R3-16, R3-22).

Every Approval of a release, data-release, physical-effect or standing release Act becomes a KLN signature record that verifies offline (R5-21, R11-38). AAL3 applies to physical-effect Acts and Acts with `controls`, since Acts have no risk class (contract 7.6). The events `act.prepared`, `act.approved`, `act.denied` and `act.committed` carry ids and states only (D-KLN-34).

[[DIAGRAM diagrams/09-agents-act-sequence.jsx: Act sequence · two-phase commit with the approval out of band]]

Read it top to bottom: solid arrows are requests, dashed arrows replies, and the highlighted arrow is the approval no model can give.

**Decision D-AGT-30:** Every byte leaving a tenant goes through one Act family, `release_data { recipient, payload, purpose, authorization }`, checked by KLN at `act.commit` (D-KLN-40). The only exception is contract section 7.6's audited local write by a human of an uncontrolled `public` or `internal` payload. *Why:* six egress paths invite the weakest (R5-06), and saving a 3MF for one's own slicer needs no approval (R12-16). *Rejected:* per-path controls; recipient records changed by ordinary Proposals; an Act for every local save. (revised in round 3)

Recipients are verified, screened `RecipientRecord`s, so one named only in agent text fails with `act/recipient_unverified`; an injected "our address has changed" email cannot redirect an RFQ (R5-05). The stage checks, in order:

1. The payload's confidentiality label against the recipient's clearance (D-KLN-41), and each `DataLicence`'s redistribution terms.
2. Restricted-party screening at every commit, against lists at most 24 hours old and recorded by version. They are the daily US Consolidated Screening List [S67], plus EU and UK lists where policy names them. Internal recipients are screened from phase 2 (contract section 13.2).
3. A `ControlAuthorization` for any payload with `controls`.
4. Audit, and from phase 3 a watermark record and expiry (KLN, ECO).

A release, change-notice or deviation plan lists its deliveries to the organization's ERP, MES and enterprise PLM under one Approval. Failed deliveries retry until it expires. Recipient-record changes follow D-KLN-41, never come from a flagged context, and take effect after 24 h with notice (KLN). Webhooks carry thin payloads without design content (ECO).

**Decision D-AGT-33:** Recurring flows use `standing_release`, a plan approved by two humans (D-KLN-41) that fixes recipients, channel, payload schema, confidentiality ceiling and an expiry of at most 12 months. Each later transfer is an effect of that plan, checked by the `release_data` stage mechanically. *Why:* an approval per ERP message or shared-branch push gets rubber-stamped or bypassed (R11-19, R10-26). *Rejected:* one approval per message; unbounded pre-approvals; exempting connectors or human pushes.

A channel is a connector, a shared branch or a mirror. Transfers are audited and summarized weekly to the approvers, and anything over the ceiling or off-schema needs an ordinary Act. Human and agent pushes to shared branches, mirror pushes and federation sync pass the same stage.

**Decision D-AGT-31:** Physical-effect Acts follow contract section 7.6: no device starts except through the restricted `start_print`, only assigned humans approve, and no remote approval confirms on site. AGT adds plan schemas and AGT-O-21, which captures the wire against real servers and simulators. *Why:* OctoPrint, Moonraker and PrusaLink start prints from an upload flag (R10-01), so an interface without a start is not enough, and nothing may move where nobody stands (R4-01, R5-18). *Rejected:* remote starts through OPC UA job methods; agent-committed transfers; static interface review alone. (revised in round 3)

- **Plans** name device class, serial, location, controller version, program number and what it replaces. The gateway checks the Approval against its pinned approver set (MFG).
- **OPC UA.** Crucible calls `Store` only in `store_machine_job`, and `Cancel`, `Clear` and `RevokeStart` only on its own unstarted jobs. Every other job method is uncallable [S69].
- **Restricted Acts** follow contract sections 7.6 and 7.1: `start_print` for material extrusion with a per-serial policy and a printer-side confirmation, `run_rig_test` for `unattended_safe` rigs.
- **Firmware.** `flash_device` leaves the target held for a person at the bench, and client flashing through `apps/platform` or WebUSB is the same Act.

These classes ship with MFG's transfers in phase 2, `store_machine_job` with the OPC UA path in phase 3, and `flash_device` with ELX's Software items in phase 3.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Two-phase Acts | Deterministic plan digest; commit after an assigned Approval | `act/plan_changed`, `act/denied` | AGT-O-9 | 1 |
| Approval requests | Cedar-assigned; inbox only; request id to the model; enrolled credentials | "Not assigned to you"; unenrolled credential refused | AGT-O-9 | 1 |
| Approval origin | Own origin and relying party; strict CSP; bound challenge; browser sessions for native clients | A main-origin ceremony fails | AGT-O-9 | 1 |
| Approval page | Contract section 7.6 contents, integrity flags, recipient banner | — | AGT-O-9 | 1 |
| Approval limits | Three pending; 24 h block after denial; report freezes the session | `act/denied_cooldown` | AGT-O-9 | 1 |
| Character rejection | Invisible, tag, bidirectional and zero-width characters refused | `act/payload_rejected` | AGT-O-9 | 1 |
| Release Acts | Digest over the approval subject; subject recomputed at commit; KLN's minimal signature records | `act/subject_mismatch` | AGT-O-9 | 1 |
| Data-release family | Recipient clearance, screening, `ControlAuthorization`, audit; local writes audited | `act/recipient_unverified`, `label/exceeds_clearance` | AGT-O-22 | 1 |
| Watermark and expiry | Watermark record and expiry on data release (KLN, ECO) | Delivery refused without them | AGT-O-22 | 3 |
| Standing releases | Fixed recipients, channel, schema, ceiling, expiry; weekly digest | Over-ceiling payload refused | AGT-O-22 | 2 |
| Physical-effect Acts | Transfer only; allowlisted OPC UA methods; restricted `start_print` and rig tests | `act/onsite_required` | AGT-O-21 | 2 |
| Firmware flashing | `flash_device` with read-back; target held for a person | `act/onsite_required` | AGT-O-21 | 3 |

## Model independence

Every guarantee lives in the server, so models differ in how well they work, never in what they may do.

**Decision D-AGT-21:** The hosted crew calls models through one Rust trait, `ModelEndpoint`, with adapters for hosted APIs and local OpenAI-compatible servers, never MCP Sampling. *Why:* MCP 2026-07-28 deprecates Sampling for direct provider APIs [S2], and one trait keeps provider choice a configuration decision. *Rejected:* Sampling (deprecated); a single provider (founder requirement and air-gapped installs).

```rust
pub trait ModelEndpoint: Send + Sync {
    fn record(&self) -> &EndpointRecord;            // weights digest or dated provider version, region
    fn capabilities(&self) -> &ModelCapabilities;   // tool calling, vision, context, structured output
    fn clearance(&self) -> &Labels;                 // the bound granted under D-KLN-41
    async fn complete(&self, req: CompletionRequest) -> Result<CompletionStream, ModelError>;
}
```

An `EndpointRecord` pins a local endpoint's weights digest or a hosted one's dated version, and registry weights are signed (R5-44). An endpoint qualifies for a role by passing its golden tasks at the role's pass^1 and pass^4 thresholds, bound to the record.

| Missing capability | Degradation |
| --- | --- |
| Vision | `visible_summary`, structured marks and `inspect.describe`; the role runs only if qualified in text-only mode |
| Native tool calling | JSON mode with schema validation and two repair retries; otherwise unqualified |
| Long context | Smaller pages, outlines before source, concise detail |
| Endpoint unavailable | Backoff, then the role's next qualified endpoint, recorded in provenance |
| No qualified endpoint | `crew/no_qualified_endpoint` with the qualification results; never a silent downgrade |

Identical behavior is claimed only for Crucible's side; every crew model call stores a CAS replay record, so a session's API calls replay exactly.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| External hosts | Any MCP 2026-07-28 client under server enforcement; `Declared` | Typed `auth` and `label` errors | AGT-O-1 | 0 |
| Hosted crew | `apps/crew` over the public SDK; per-tenant instances | `crew/no_qualified_endpoint` | AGT-O-15 | 2 |
| Endpoint records | Weights digest or dated version; re-qualification on change | Unqualified endpoint refused | AGT-O-10 | 2 |
| Qualification and degradation | Per-role suites and thresholds; declared degradations | Never a silent downgrade | AGT-O-15 | 2 |
| Replay records | Every crew model call in CAS | — | AGT-O-10 | 2 |
## Benchmarking and training data

Agent quality is measured and gated like any feature. Harness, suites and graders live in `oracles/agents/`, and held-out suites outside every tree agents read. Third-party datasets are fetched by content hash at test time, never vendored.

| Suite | What it measures | Use |
| --- | --- | --- |
| Text2CAD-Bench | Text to parametric CAD at four levels; 600 examples [S16] | External comparison on exported geometry |
| CADPrompt | 200 prompts; point-cloud distance, compile success [S17] | External comparison |
| CADTestBench | Text to CAD verified by executable tests [S18] | Reference for check-based grading |
| MUSE | Manufacturable assemblies; strongest models scored 19–21% on fine-grained criteria [S19] | Phase 2 and later |
| Golden-product tasks | Create, edit, fix a check, add a study, DFM, CAM, change order; at least 50 per product (target) | Primary metric, release gate, qualification |
| Held-out set | The same on unseen products; at least 200 by phase 2 (target) | Overfitting control |
| Injection suite | Planted instructions in imports, comments, identifiers, string literals, templates, embossed geometry and textures; at least 100 per release (target), as AgentDojo [S34] | Security gate |

Text2CAD-Bench's metrics are reimplemented from the paper, since its code was unreleased [S16]. Golden tasks carry a starting Change, goal, hidden acceptance checks, reference solution and forbidden actions, graded by `service:ci` in two platform classes. A model judge scores only documentation and requirement text, on a 0.0–1.0 rubric [S33] calibrated by humans each release.

Metrics include task success, pass^1 and pass^4, edit minimality, query robustness, review acceptance, verifier catch rate, cost per success and safety violations. Reliability across trials is gated, since τ-bench found pass^8 below 25% in its retail domain [S35].

Every release, and every change to `std::agents`, `apps/crew` or the MCP surface, reruns golden tasks and the held-out set three times per endpoint. The gate fails on a success drop above 2 points (target) at 95% confidence by paired bootstrap, or on any injection. Red-teaming adds adaptive attackers [S34], an outside red team before each gate, tripwires and a public bounty from phase 3.

Models adapt through context first and are fine-tuned only where measurement shows a gain. The generator emits Ingot programs, edits, repairs of injected errors and observations paired with facts. Every item builds and reproduces from its seed, as CAD-Recode's million procedural sequences did [S20].

| Source | Terms | Use |
| --- | --- | --- |
| Fusion 360 Gallery Dataset | Non-commercial research only; terminable by Autodesk [S21] | Never in anything that ships, in any tab |
| ABC dataset | Onshape's terms, varying by document date and LICENSE tab [S22][S23] | Only contract section 13.3's licence-filtered subset with ECO's per-model evidence: benchmarks and published measurements; training as D-AGT-22 allows |
| DeepCAD and derivatives | Parsed from Onshape public documents linked from ABC [S64] | As ABC, model by model |
| Public CAD benchmarks | Licences not stated on the pages opened [S16][S17][S18][S19] | Evaluation only, after licence review |
| Procedural data, std, golden products | Crucible's own | Unrestricted |
| Customer data | Owned by the customer | Opt-in only |

**Decision D-AGT-22:** Every shipped model trains only on procedural data, std, golden products, opted-in customer data, and data whose commercial licence has per-item evidence. Cross-tenant training admits only `public` items or a `DataLicence` permitting it, never `confidential` items or third-party Assets. *Why:* weights inherit data obligations, Fusion 360 Gallery forbids commercial use [S21], customers own their geometry (R5-28, R5-33), and Onshape's grant varies per document (R11-33). *Rejected:* research-use exceptions, ECO's segmentation models included; scrubbed confidential corpora; scraped CAD models; dataset-level licence assumptions. (revised in round 3)

Per-tenant weights serve one tenant. Opt-in is off by default and set per repository by two humans, with eligibility per item. Shared corpora are deduplicated, exclude identities and comments, and must not leak planted canaries, and a withdrawal removes affected shared models within 30 days.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Benchmark harness | Suites above, graded by checks in two classes; datasets fetched by hash | — | AGT-O-15 | 1 |
| Release gate | Three trials per task per endpoint; 2-point drop at 95% or any injection fails | Release blocked | AGT-O-15 | 1 |
| Injection suite | Planted instructions across every text and image channel | Gate fails on any success | AGT-O-8 | 1 |
| Verifier efficacy | Planted-defect catch rate | Gate fails below target | AGT-O-19 | 2 |
| Procedural corpus | Items build; reproducible from seeds | Failing items excluded | AGT-O-23 | 2 |
| Training eligibility | Per-item labels, licences and evidence; canary tests; 30-day withdrawal | Ineligible items excluded and reported | AGT-O-23 | 3 |

## Agent-facing documentation

**Decision D-AGT-23:** All agent-facing documentation is generated from the Rust method types, Ingot doc comments and the error catalog, pinned to versions and compiled in CI. A failing example blocks the release, and `read.docs` answers for the repository's lockfile, never the latest release. *Why:* stale docs teach agents wrong APIs, and version-pinned answers match the code the agent edits. *Rejected:* hand-written agent docs (drift); retrieval over the web (unversioned, untrusted).

Crucible publishes per-method and std references, an error catalog with examples and fixes, skills and a `llms.txt` index. Pages run about 2,000 tokens (target) and are benchmarked like code, because tool descriptions measurably help agents [S31]. A grant exposes at most 60 tools, and a new method needs a benchmark gain over composing existing ones [S31]. Deprecations carry a machine-applicable fix for 12 months, and CI fails a public std item without a doc comment, example or units.

| Capability | Contract | Failure | Oracle id | Phase |
| --- | --- | --- | --- | --- |
| Generated references | Methods, std and errors from source, pinned to versions | A failing example blocks the release | AGT-O-16 | 0 (errors), 1 (std) |
| Lockfile-pinned answers | `read.docs` for the repository's lockfile | `docs/not_found` with nearest matches | AGT-O-16 | 1 |
| Tool surface | At most 60 tools per grant; group prefixes | A new method without benchmark gain is refused in review | AGT-O-15 | 1 |

## State of the art

| Component | Best published method | Leading implementation to beat | Crucible's choice | How we measure |
| --- | --- | --- | --- | --- |
| Agent protocol | MCP 2026-07-28 with Tasks and Skills [S1][S2][S4][S8] | Fusion MCP and Fusion Data MCP [S13][S14]; Onshape FeatureScript MCP [S24] | Adopt; one catalog behind every transport, with a published approval model (D-AGT-1, D-AGT-2) | AGT-O-1; transcripts pass on 5 MCP hosts (target) |
| Conversational CAD agents | Code as the medium, selection awareness, four-view self-review [S11][S12] | Zoo Zookeeper [S11][S12]; NX Copilot, which answers but does not act [S42][S43] | Ingot, `session.presence`, `Grid4`; independent verification | AGT-O-15 |
| Tool and response design | Consolidated, namespaced tools; concise responses; actionable errors [S31][S32] | Claude Code's 25,000-token limit [S31] | At most 60 tools per grant; `detail`; a 20,000-token cap | Tokens per successful task |
| Errors and retries | RFC 9457 [S45]; tool execution errors [S3]; Idempotency-Key [S46] | — | D-AGT-6, D-AGT-7 | First fix resolves at least 60% (target); AGT-O-5 |
| Delegated identity | MCP's OAuth 2.1 profile [S6]; token exchange [S47]; DPoP [S58] | — | Delegation grants, sender-constrained tokens (D-AGT-28) | AGT-O-7, AGT-O-24 |
| Prompt-injection defence | Design patterns [S25]; CaMeL, 77% of AgentDojo tasks with provable security against 84% undefended [S26]; FIDES labels [S27]; Rule of Two [S28] | CaMeL [S26] | Context labels, four instruction sources, Plan-Then-Execute, Dual LLM extraction, approved Acts (D-AGT-18, D-AGT-24, D-AGT-25). Deviation: no CaMeL interpreter around every role. *Reason: maturity;* phase 3 evaluates one for tainted roles | Zero attacker-chosen consequential actions; utility under attack within 10 points of clean (targets) |
| Visual grounding | Set-of-Mark prompting [S36] | Zookeeper's multi-view snapshots [S11] | Marks with structured maps, `Grid4`, text summaries (D-AGT-9) | Entity-selection accuracy at least 95% (target) |
| Snapshot comparison | ꟻLIP perceptual difference [S62] | — | ꟻLIP thresholds against a pinned renderer image | AGT-O-3 |
| Design verification | CADCodeVerify [S17]; executable tests [S18] | CADCodeVerify [S17] | Checks plus a mutating verifier (D-AGT-12) | Catch rate at least 90% by phase 2 (target, AGT-O-19) |
| Orchestration | Orchestrator-workers [S32]; parallel subagents [S33] | Anthropic's research system [S33] | Validated plans, branches, a merge queue; one agent by default (D-AGT-13) | Success and cost against one agent |
| Fair sharing | Dominant Resource Fairness [S65] | — | Within each priority class | AGT-O-11 |
| Expensive optimization | qLogNEHVI [S37][S38]; hypervolume knowledge gradient [S39]; scaled priors [S40] | BoTorch 0.18.1 [S38] | `std::explore` in Rust (D-AGT-15) | Hypervolume within 5% of BoTorch (target) |
| Cheap optimization | NSGA-II and NSGA-III [S41] | pymoo 0.6.2 [S41] | The same in `std::explore` | Hypervolume against pymoo |
| Text-to-CAD and editing | Text2CAD-Bench [S16], CADPrompt [S17], CADTestBench [S18], MUSE [S19], CadEval [S44] | Text2CAD-Bench L1: GPT-5.2, invalidity 11.1%, IoU 0.59 [S16] | Ingot agents in check-driven loops | Adapted L1: invalidity at most 5%, IoU at least 0.75 (target) |
| Reliability | pass^k [S35] | — | pass^1 and pass^4 per suite and endpoint | Release gate (AGT-O-15) |
| Training data | Procedurally generated CAD programs [S20] | CAD-Recode [S20] | An Ingot generator whose items build (D-AGT-22) | Gain on the held-out set |
| Provenance | in-toto Statement v1 [S48] | — | Signed `ChangeProvenance` | AGT-O-10 |
| CAM assistance | Strategies accepted step by step [S15] | CloudNC CAM Assist [S15] | CAM programmer gated by collision and gouge checks | 50% of golden programs accepted unedited (target) |

## Platform notes

- **Desktop.** `crucible mcp` runs on stdio with the keychain credential [S6], and each launch joins the (user, client identity) label. Local SDKs use a domain socket or named pipe, never an open localhost port [S7].
- **Desktop without a team server.** Read, Edit, Evaluate, Inspect and Compare run locally with audited exports. Proposals and Acts need a team server (contract section 13.2).
- **Browser.** Agents use the TypeScript SDK over Streamable HTTP to a team server; the page links `core/api` as Wasm and runs no models.
- **Servers.** `apps/mcp`, `apps/crew` and `apps/model-gateway` ship as Linux containers for x86-64 and ARM64; Proposal CI runs in microVMs.
- **Air-gapped installs.** Local endpoints, bundled docs, skills and suites, qualification on site, no external MCP servers.
- **Approvals.** Clients open the approval origin in a browser session; tablets approve with enrolled credentials, phones never (contract section 7.6).
- **Snapshots.** Byte identity holds only on the pinned lavapipe CI image [S61]; elsewhere ꟻLIP thresholds apply.
- **Portability.** Python and TypeScript SDKs are pure-language, and the Rust SDK builds for every Tier 1 target, `wasm32` included. Paths are repository-relative, forward-slash and NFC, and no agent function needs a GPU.

## Interfaces with other subsystems

### What AGT provides

| To | Provides | Types |
| --- | --- | --- |
| All tabs | The `api` catalog; sessions; boundary labels; budgets; idempotency; the error namespace; audit payloads | API method |
| ING | `SourcePatch` application; `evaluate.subscribe` and `edit.stream` under `LiteralSite` overrides; untrusted spans and strings as handles | API method |
| KLN | Admission; `Budget` and `PriorityClass`; `release_data` and standing releases (D-AGT-30, D-AGT-33); context labels on writes; Proposals, risk classes, auto-merge; audit payloads; `act.*` events | `Budget`, `Proposal` |
| UIX | `inspect.render`, `inspect.ask_render`; `evaluate.subscribe` and `edit.stream`; `read.language_service`; `session.ask` and `session.*` events; Proposals with verifier reports and provenance; `ActPlan`s, approval requests and the approval origin's rules (D-AGT-20); `session.control` | `Proposal`, `ActPlan`, `ChangeProvenance` |
| MFG | Physical-effect, `request_quote` and `publish_passport` Act classes and plan schemas; `read.machine_data`; the CAM programmer | Act class |
| ELX | `flash_device`; `edit.stream` and `edit.apply`; datasheet extraction, labelled `data_untrusted`; budget caps for long tool runs | Act class, Proposal |
| ECO | Catalog entries for ECO's methods; `crucible:api`; Act classes and `release_data`; `ExternalText` and instruction authority; image rules (D-AGT-26); `std::agents` and `std::explore` | Package, Act class |
| PLT | Canonical JSON; the `ApiError` shape for `Guidance` errors; `Usage` as the resource record | `Usage`, `ApiError` |
| Every tab that ships a model | The training-data rule (D-AGT-22) | — |

### What AGT requires

| From | Requirement |
| --- | --- |
| ING | Diagnostics with `SourcePatch` fixes; the formatter; the language service; tool-schema metadata; doc comments and templates; `ExternalText` and span integrity on evaluated strings; `LiteralSite`; `CheckOutcome` and the gate predicate; `#[was]` |
| KLN | Evaluations with priority classes, work budgets and Aborts; unshared override keys; labels, write-down and integrity cleared by merge; Changes, semantic merge and diffs; span integrity; `RecipientRecord` clearances; the `release_data` stage (D-KLN-40); declassification, Waiver, `ControlAuthorization` and minimal signature records in phase 1; the audit log; the two-person list and break-glass (D-KLN-41); `retention_basis`; `evaluation.*` events; Cedar |
| ANV | Entity provenance; `Query` resolution with fixes and `NearTie`; `anvil::query_stability` reporting `RankSwap`; measures, sections and geometry diffs |
| FLX | Studies; regularized goals; `ErrorBudget`s and zones; `SolvePlan` explanations; cost estimates; Field sampling; gradients and surrogates for `std::explore` |
| COV | Validity envelopes; the coverage map and limit records; typed `ValidityError`s with escalation |
| UIX | The renderer `apps/headless-render` links, with `RenderProfile`; the Proposal view; the approval page; steering controls |
| MFG | Payload kinds; DFM rules; CAM; cost with intervals; `MfgError` fixes; `apps/machine-gateway` with connector allowlists, program registry and pinned approvers |
| MEC | Std features with doc metadata; tolerance stacks; `SolveReport`s, `ContinuityReport`s and check Fields |
| ELX | Electronics checks; Proposals from layout tools; datasheet record templates; board hazards for `flash_device` pages |
| ECO | Signing for `std::agents` and `std::explore`; licence metadata and ABC evidence; registry, events and archives; importers emitting `ExternalText`; worlds importing `crucible:api`; `release_data` members; CLI exit codes |
| PLT | Transport, `Usage` measurement; `CredentialStore`; the stdio MCP sandbox; the `Interactive` pool lane; browser sessions and `Authenticator` |

## Oracles

Oracles live in `oracles/agents/`, readable but never writable by agents; held-out suites and tripwires live outside it.

| Id | Verifies | Pass criterion |
| --- | --- | --- |
| AGT-O-1 | MCP, Skills and schema conformance | Tools and `structuredContent` validate; skills match manifests, and hosts without extensions work; fuzzed requests yield `<family>/<code>` errors; Tasks, polling and SDK streams agree |
| AGT-O-2 | SDK and WIT parity | Golden transcripts give byte-identical canonical JSON through every SDK and raw MCP; the published `crucible:api` WIT matches the Rust types |
| AGT-O-3 | Observation determinism | Scene graphs and descriptions identical across classes; snapshots byte-identical on the pinned image, elsewhere mean ꟻLIP at most 0.05 (target) |
| AGT-O-4 | Description integrity | Every number maps to a fact; perturbing a fact changes the text; third-party phrasing appears only as handles |
| AGT-O-5 | Idempotency | Injected drops and duplicates yield zero duplicate Changes or Acts |
| AGT-O-6 | Concurrency and drag streams | A TLA+ model checks; multi-writer tests lose no update and catch every stale base; an `edit.stream` ends in one Change, and no overridden result is shared |
| AGT-O-7 | Policy enforcement | A reference evaluator agrees with the server over scopes, methods, protection, labels, clearances, chains of depth 1 to 3, KLN's two-person list and every forbidden action under break-glass |
| AGT-O-8 | Injection resistance | Zero attacker-chosen consequential actions, via doc comments, identifiers, templates, textures or a host with a fetch tool. Part names, BOM text, notes, diagnostics and embossed text from a tainted context, merged by a human, reach clean contexts only as handles; endorsement from the authoring chain is refused. Write-down and label laundering count as successes |
| AGT-O-9 | Act integrity | Unapproved commits, changed plans, replays, forwarded links, author-chosen names, hidden characters, approval spam and chain-internal R3 or R4 approvals are refused. Unenrolled or synced credentials and scripted main-origin pages cannot approve. Swapped firmware, Material versions or documents fail with `act/subject_mismatch`. The page renders every physical-effect class, and signed Approvals have KLN records |
| AGT-O-10 | Provenance | Every Change carries a valid signed statement with complete fields, including the endpoint record; tampering is detected |
| AGT-O-11 | Budgets and rate limits | Spend never exceeds a cap by more than one safe-point interval; limits and fair shares hold; declared tokens are never enforced |
| AGT-O-12 | Plans and leases | Invalid generated plans are rejected and valid ones pass; stale-lease writes are always rejected; held-out grading is unreadable by workers |
| AGT-O-13 | Exploration | Hypervolume within 5% of the references (target); equal seeds give identical synchronous sequences; failures counted |
| AGT-O-14 | Risk classes and auto-merge | A labelled corpus gets the expected classes: loosening, waivers and tainted changes are R3 or higher; no `data_untrusted` change is R1; external-host Proposals are at least R2; a clean R1-shaped change on an assembly with a merged supplier part is R1. Auto-merge refuses everything outside policy |
| AGT-O-15 | Agent quality gate | Golden tasks and the held-out set meet the regression thresholds per release and endpoint |
| AGT-O-16 | Docs | Every example builds and its checks pass; every public std item has a doc comment, an example and units |
| AGT-O-17 | Clearance and write-down | Tripwires never reach uncleared contexts or lower-labelled repositories; undeclassified writes down fail; `Declared` endpoints get nothing above `internal`. A tainted edit to a clean branch succeeds at R3, and endorsement changes integrity without declassification. Concurrent grants, re-authorization and stdio relaunch keep the label; only `session.reset_context` clears it |
| AGT-O-18 | Query robustness | Scores agree with a labelled set of robust and fragile queries; seeded swaps the design samples report `RankSwap` with the sample; `NearTie` reaches the agent; no score claims a guarantee |
| AGT-O-19 | Verifier efficacy | The planted-defect catch rate meets its target; reviews from the author's delegating human in an unattested host are marked `Declared` |
| AGT-O-20 | Audit | One entry per call in KLN's log; no entry holds labelled bytes; shredding an identity key leaves the log verifiable and the person unidentifiable |
| AGT-O-21 | Physical safety | Under wire capture against real servers or simulators (OctoPrint, Moonraker with Klipper, PrusaLink, URSim, controller simulators), no transfer carries a start semantic and every device stays idle. No plan schema expresses a start, and only allowlisted OPC UA methods are called. `start_print` without a per-serial policy, extrusion or a printer-side confirmation within 10 minutes is refused; `flash_device` leaves the target held; `run_rig_test` needs `unattended_safe`; no remote approval confirms on site |
| AGT-O-22 | Data release | Every egress path runs the stage, and local exports only when controlled or above `internal`; failing recipients, scope and licence mismatches and a party listed the day before are refused; recipient changes show the banner; standing releases refuse over-ceiling or off-schema payloads |
| AGT-O-23 | Training data | Eligibility follows labels, licences and per-item evidence; canaries are not extractable; withdrawals complete within 30 days |
| AGT-O-24 | Delegation grants | Exchange without a live grant, for non-agent scopes, or for Approvals or `policy:admin` is refused; tokens are sender-constrained |

## Phasing

No AGT capability is in contract section 13.4's table; each row follows its owner's phase for what it rests on.

| Phase | AGT contribution to the gate |
| --- | --- |
| 0 | `core/api` types and schemas in single-principal mode; Session, Read, Edit and core Evaluate methods; idempotency; the error namespace and the docs pipeline; MCP server on stdio and HTTP; the Rust SDK; source-level descriptions. AGT-O-1, 2, 4, 5, 6 and 16 green |
| 1 | GP1 and GP2 worked by agents through external MCP hosts: enforcement of scopes, labels, budgets and approvals; Inspect, Compare, Propose, CI reports and risk classes; context labels and resets; drag streams; `crucible:api`; release and export Acts on the approval origin, used in the physical dry run (contract section 13.2, chain D); Python SDK; three roles. The golden-task harness, injection suite and qualification run on at least two endpoints and report pass^1 and pass^4. AGT-O-7, 8, 9, 14, 17, 20 and 22 green |
| 2 | Hosted crew, delegation grants, model gateway and extraction; TypeScript SDK; nine further roles; swarms; exploration; auto-merge; standing releases; physical-effect and remaining data-release Acts. Swarm tasks on GP3 and GP4 beat the single-agent baseline at no more than 3× its cost (target); AGT-O-21 and 24 green |
| 3 | Hypervolume knowledge gradient; training opt-in with canary tests; a public bounty; an interpreter evaluated for `instruction_tainted` roles; `publish_passport`; `flash_device`; watermark and expiry on data release. Golden tasks on GP5 report pass^1 and pass^4 on every qualified endpoint |
| 4 | Validation against physical test data with correlation checks. GP6 explorations confirm at least 3 Pareto-optimal variants at `SignOff` (target) |
| 5 and later | A compliance-evidence role |

## Open questions

1. **R1 thresholds.** Are a 90% margin floor, 0.5 mm deviation and 1% cost increase right? They stay defaults until auto-merge ships in phase 2, whose review data can set them.
2. **Findings declined in part.**
    - R11-12: an unattested verifier review shows as `Declared` and needs a human approval beside it. It still counts, so a solo phase 1 user can merge.
    - R12-02: the work item maps onto `WorkItem`, but plans ship in phase 2, so contract 13.2 runs the `WorkItem` record over Git until then (CCR-AGT-13).
    - R11-19: standing-release transfers are effects of one approved plan; contract section 7.6 says so (CCR-AGT-10).
    - From round 2: R3-53 (title fixed); R4-01 (physical Acts in phase 2); R5-18 (contract names stand). R4-05 (MFG owns headers, offsets and drip feed); R6-02 item 6 (three phase 1 roles).

## Contract change requests

- **CCR-AGT-7.** Passing every check: accepted in contract v5, section 7.6.
- **CCR-AGT-8.** Rig tests as a restricted Act: accepted in contract v5, sections 2 and 7.6.
- **CCR-AGT-9.** Owners of `Budget` and `PriorityClass`: accepted in contract v5, section 5.
- **CCR-AGT-10.** Standing releases: accepted in contract v6.1, section 7.6.
- **CCR-AGT-11.** AAL3 for Acts: accepted in contract v6.1, section 7.6.
- **CCR-AGT-12.** Error codes: accepted with CCR-KLN-9 and CCR-ECO-11 in contract v6.1, section 7.6.
- **CCR-AGT-13.** Build-program bootstrap: accepted in contract v6.1, section 13.2.

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
- [S21] Fusion 360 Gallery Dataset license: https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md and https://raw.githubusercontent.com/AutodeskAILab/Fusion360GalleryDataset/master/LICENSE.md
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
- [S49] 15 CFR 734.18, activities that are not exports (eCFR): https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734/section-734.18 and Cornell LII: https://www.law.cornell.edu/cfr/text/15/734.18
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
- [S63] Claude API, "Define tools" (tool `name` must match `^[a-zA-Z0-9_-]{1,128}$`): https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
- [S64] DeepCAD repository README ("parsed from Onshape public documents with links from ABC dataset"): https://github.com/ChrisWu1997/DeepCAD
- [S65] Ghodsi et al., "Dominant Resource Fairness: Fair Allocation of Multiple Resource Types" (NSDI 2011): https://www.usenix.org/legacy/event/nsdi11/tech/full_papers/Ghodsi.pdf
- [S66] BoTorch documentation, introduction: https://botorch.org/docs/introduction
- [S67] US International Trade Administration, Consolidated Screening List: https://www.trade.gov/consolidated-screening-list
- [S68] Apple Developer, "Supporting passkeys": https://developer.apple.com/tutorials/data/documentation/authenticationservices/supporting-passkeys.json
- [S69] OPC Foundation, OPC 10031-4 (OPC UA for ISA-95, Part 4: Job Control) v2.00, section 6.3: https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3
