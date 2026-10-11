# R5 Security and legal review

Summary:
1. The label and taint model is unsound. Labels do not follow data through an agent's context: there is no write-down rule, and typed untrusted values never taint. Human endorsement also turns agent-written free text in Ingot source into trusted instructions for later sessions and for the verifier (R5-01, R5-02).
2. The CI runners and workers that sign shared-cache attestations also run untrusted Proposals and supplier native code. A 1% spot check cannot catch a targeted poisoning of a release Check, and no rule stops one tenant's builders from writing the global public cache domain (R5-03).
3. Two-phase Act approval does not keep the approval out of the agent's channel. URLs pass through the model and host, any authorized approver can approve a forwarded plan, and file names are author-chosen, so a hijacked agent or an insider can get an irreversible effect approved (R5-04).

### R5-01 · Critical · Targets: AGT, KLN, CONTRACT
**Section:** AGT Safety and security (Untrusted content is data; Taint and the Rule of Two; Data classes and model endpoints); KLN Security (Export control); contract §5 `Labels`, §7.6
**Problem:** Kiln joins labels through derivations, but an agent's model context is a derivation path the design never labels. A session that reads ITAR content in one repository can write it, unlabeled, into another, because no write-down rule exists. An external host that opens one session per repository mixes them without Crucible knowing. Untrusted typed values (numbers, enums, `SuggestedFix` edits returned by third-party packages) are declared non-tainting, so they can steer a "clean" session's edits and re-enter the design as trusted literals that qualify for auto-merge.
**Evidence:** AGT: "Typed numbers with units, enums, `EntityId`s and identifiers that Crucible generates cannot, so untrusted values of those kinds keep their label but do not taint a session that reads them." Contract §5: Labels are "Joined through every derivation by Kiln and enforced by `api` at every boundary". Contract §7.6 taints a session only when it reads "raw text". `SessionOpen` binds one repository, and nothing joins labels across the sessions of one host. AGT's own rule, "derived values take the most restrictive combination of their inputs", applies to the model's output as much as to a Kiln node, but the design never labels the context that produces it. 22 CFR 120.56 defines release of technical data to include inspection by, and oral or written exchanges with, foreign persons (https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.56), so an unlabeled copy that later reaches a supplier or a hosted model is a spill.
**Fix:** (1) Every model context carries a label: the join of the labels of every value returned to it, typed or textual. For the hosted crew the context is the conversation. For external hosts it is the OAuth token family (client instance plus user), shared by every session that family opens. (2) Split integrity into `instruction_tainted` (free text or images read) and `data_untrusted` (any untrusted value read). (3) Every write (edit, Proposal, comment, review, exploration record, Act payload) carries at least the context's confidentiality label and data-integrity flag. A write to a destination with a lower label fails with `label.write_down` unless a declassification record signed by two people, one of them an `export_officer`, names it (R5-15). (4) Return untrusted typed values by handle (`ValueRef`), and let edits cite the handle (`SetParameter { value: FromRef(h) }`) so the label follows exactly. Label `SuggestedFix`es from third-party code untrusted, and forbid them to add dependencies or touch Checks, tolerances, policy files or protected paths. (5) Auto-merge and class R1 require `data_untrusted == false` for every authoring context. (6) Extend O-AGT-8 and O-AGT-17: write-down and label-laundering attempts count as successful attacks, and tripwire strings from `export_controlled` repositories must never appear in a lower-labeled repository.

### R5-02 · Critical · Targets: AGT, KLN, ING, CONTRACT
**Section:** AGT Untrusted content is data (trusted origins; Endorsement), Independent verifier, Text descriptions (D-AGT-10)
**Problem:** Only import-derived strings are wrapped in `external(...)`; comments, doc comments, string literals, identifiers and description templates that an agent writes into Ingot are ordinary source. The verifier reads the Proposal's design untainted, so an author agent can address it in a comment. Once a human merges the Proposal, endorsement makes that text trusted on `main` permanently, where every later "clean" session and canonical `inspect.describe` output read it. D-AGT-18's guarantee that untrusted content "can never become instructions" is therefore false.
**Evidence:** AGT trusted origins include "Ingot source on protected branches". AGT: "When a human approves and merges a tainted Proposal, its content becomes trusted on the target branch. This covers geometry, parameters and source the human reviewed." The verifier "sees the requirements, the design, the semantic diff, the CI report and the rationale's structured fields". D-AGT-10 context: "a feature's doc metadata supplies its phrasing", and only "Templates from unverified publishers are untrusted text". The non-tainting exemption covers "identifiers that Crucible generates", not identifiers an agent writes.
**Fix:** (1) `repo` keeps span-level integrity provenance: each source span records the integrity of the context that wrote it, and merges preserve it. (2) `read.source`, `read.outline`, `read.docs` and `inspect.describe` return free-text spans as `ExternalText` handles when their author is outside the reader's delegation chain or their integrity is untrusted. Free-text spans are comments, doc comments, string literals, description templates, and identifiers not produced by the compiler or typed by a human. (3) Narrow endorsement: a human merge endorses structure and typed values, never free text. Free text becomes trusted only through an explicit per-span "endorse text" action that shows it verbatim, with invisible and bidirectional characters highlighted. (4) The verifier reasons over a typed view (IR, semantic diff, Check results) with the author's free text elided. (5) Add injection-suite cases: an instruction planted in a merged doc comment, identifier or description template must not change a later clean session's actions or the verifier's verdict.

### R5-03 · Critical · Targets: KLN, CONTRACT, AGT, FLX, ELX, COV
**Section:** KLN Distributed and remote evaluation (D-KLN-9), Threat model (Cache poisoning); contract §7.1 (Kiln)
**Problem:** The machines allowed to sign shared-cache attestations (CI runners and organization workers) also evaluate untrusted Proposals and run untrusted native code as External Ops (supplier FMUs, IBIS-AMI DLLs, emulators) inside ordinary Linux containers. One escape yields a signing identity that can map any `OpKey` to any output, and 1% spot re-execution catches a poisoned entry that a release consumes once with probability 0.01. Every tenant shares the global public cache domain, and no trust rule stops one tenant's builders from poisoning std results for all of them.
**Evidence:** D-KLN-9: "Only trusted builders write the shared result cache: CI runners and the organization's workers." KLN: "Kiln continuously re-executes 1% of shared cache hits"; residual risk "A compromised CI worker, caught statistically by spot re-execution". COV: "External tools run only in Linux containers on team servers or cloud workers (D-COV-12)". FLX: "FMUs from outside Crucible are untrusted native code." KLN: values with all-public inputs "live in one global public domain that every tenant shares".
**Fix:** (1) Split the worker pools. `untrusted-eval` workers run Proposal CI from agent and external branches and every External Op, in single-use microVMs (Firecracker- or gVisor-class). They hold no attestation key and write only to a per-Proposal namespace. `trusted` builders evaluate only merged protected-branch revisions. (2) A separate attestation service holds the signing keys and signs `(OpKey, ObjectId)` only for jobs dispatched to trusted builders, bound to workload identity. (3) Release gates and every `SignOff` Check accept a cached result only when two independent trusted builders produced the same `ObjectId` (different hosts; for `Portable` operations, different ISAs); otherwise they recompute. (4) Only the operator's own fleet writes the global public domain, with 2-of-n agreement. The default client trust policy is "own organization plus operator public signers". (5) Weight spot re-execution by downstream fan-out, at 100% for nodes that feed released Checks. (6) Hardware runners sign measurements with TPM-held device keys under measured boot. Reword contract §7.1 to: "Only trusted builders evaluating trusted inputs write the shared cache."

### R5-04 · Critical · Targets: AGT, UIX, KLN, CONTRACT
**Section:** AGT Irreversible real-world actions (D-AGT-20), MCP profile; UIX Approving and rejecting, Approvals, Platforms and devices
**Problem:** D-AGT-20 claims "the approval never passes through the agent's channel", but the approval URL does: the client presents it, and without elicitation support it returns to the model in `context`. Because any "approver with the required authority" may approve, a hijacked agent, compromised host or insider can prepare a plan and forward its genuine Crucible URL to a busy approver. File names in `Effect::SendFiles` come from the plan's author, so the human approves a name while the digest names other content. There are three approval surfaces (UIX's "secure dialog", AGT's approval page, the planned MCP Apps viewer inside the host), and phones may approve although the contract makes them viewers.
**Evidence:** MCP: "URL mode elicitation returns a URL that an attacker can use to send to a victim. The MCP Server **MUST** verify the identity of the user who opens the URL before accepting information." (https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation). AGT: "A client that does not support elicitation receives `act.approval_pending` with the approval URL in `context`"; "Approval requests reach the delegating human, or an approver with the required authority". UIX: "explicit human confirmation through the platform's secure dialog"; "The phone app shows saved views, comments, approvals". Contract §9: "phones as viewers".
**Fix:**
1. Make an approval request a server record assigned to named approvers by Cedar policy, delivered only to their Crucible inbox. Push notifications carry no content. Anyone else who opens the URL sees "not assigned to you".
2. Never return the approval URL to the model; `act.approval_pending` carries only a request id.
3. The server generates the approval page: file names from item number, revision, format and release tag; a server-rendered thumbnail; a content summary (Items, labels, bytes); the recipient's verification and screening dates; a diff against the last approved plan of the same class to the same recipient; and the session `purpose`, marked as agent text.
4. Require phishing-resistant WebAuthn user verification. R4 classes can be approved on desktops and tablets only.
5. Allow at most 3 pending requests per session. A denial blocks re-preparing a plan to the same recipients for 24 h and offers "report as suspicious", which freezes the session.
6. Reject invisible characters, Unicode tag characters (U+E0000 to U+E007F), bidirectional controls and zero-width characters in free-text payloads (`notify_external`, RFQ notes).
7. Make the MCP Apps viewer read-only, and make UIX's secure dialog this same page.
8. Extend O-AGT-9: approvals from a forwarded URL by a non-assignee, plan substitution, hidden characters and approval spam are all refused.

### R5-05 · Major · Targets: AGT, KLN, MFG
**Section:** AGT Irreversible real-world actions (verified recipients); KLN Secure supplier collaboration; MFG Sourcing and supply chain
**Problem:** Every send Act depends on a "supplier registry" of verified recipients, but no tab specifies it: AGT says MFG does, and MFG has only supplier capability records. Unless specified otherwise, recipient endpoints change through ordinary Proposals. A datasheet or supplier email saying "our RFQ address has changed" can therefore reach an endorsed record (R5-02), and every later approved RFQ goes to the attacker. This is business-email compromise through endorsement.
**Evidence:** AGT: "Recipients must be verified records in the organization's supplier registry, which `repo` stores and the MFG tab specifies." MFG's only supplier records are "Processes, machine envelopes, materials, tolerances, certifications ... as signed, dated data packages".
**Fix:** KLN defines `RecipientRecord` with these fields: organization; endpoints (email domains, API hosts, partner-connector ids); verification method and date (an out-of-band callback to a previously verified contact); restricted-party screening result and date; clearance attributes (US-person status, country); and expiry. Recipient records are policy data (R4). A change needs `policy:admin` plus a second human, cannot come from a context with `data_untrusted` or `instruction_tainted`, and takes effect after 24 h with notice to the previous contact. An Act to a recipient changed in the last 7 days shows a banner on the approval page.

### R5-06 · Major · Targets: AGT, ECO, KLN, MFG
**Section:** KLN Secure supplier collaboration; AGT Irreversible real-world actions (Act classes); ECO Manufacturing partners, Repository access and the exit guarantee
**Problem:** Data leaves a tenant through at least six paths with different controls: KLN supplier packages have watermarks, screening and expiry, while AGT Acts have recipient verification and approval. ECO's partner `request-quote` carries release Files without being declared an Act. The Git mirror and `archive.export` are plain API methods although the contract makes export an Act. Agent writes on branches shared with an external organization reach that organization with no Act at all.
**Evidence:** ECO: "A `quote-request` names a release by its signed tag and carries content-addressed Files ... Orders are Acts" (RFQs are not). Contract §7.6: "publish, yank and export are Acts". ECO: Git mirror is "A one-way export of the Ingot sources, manifests and lockfiles to a Git repository". KLN: suppliers return feedback as "a Proposal on a branch shared with them".
**Fix:** Route every byte leaving a tenant through one Act family, `release_data { recipient, payload, purpose, authorization }`. Every member runs the same checks at commit:
- labels against recipient attributes;
- restricted-party screening;
- for `export_controlled`, an export authorization record (license number, license exception or exemption);
- a watermark record, expiry and audit.

ECO states that `request-quote` runs only inside a `request_quote` Act, and that the Git mirror, `archive.export` and passport publication are Acts. Branches shared with external organizations are external surfaces: agent writes there need `share_external` and are refused to tainted contexts.

### R5-07 · Major · Targets: AGT
**Section:** AGT Two ways to bring a model; Exfiltration controls; Scopes (`external:read`)
**Problem:** For external MCP hosts, the taint rules govern only effects inside Crucible. A host with its own web-fetch, email or chat tools completes the lethal trifecta once its model reads `read.external_text`. It then holds the injected instructions, Crucible data and an outbound channel Crucible cannot see. The hosted crew has the same exposure whenever policy grants a role web access.
**Evidence:** AGT: "For external MCP hosts, Crucible cannot see or control what the host does with returned content." AGT: "no general web access unless a role needs it and policy grants it". Meta: an agent with all three properties "requires supervision"; prompt injection is "a fundamental, unsolved weakness in all LLMs" (https://ai.meta.com/blog/practical-ai-agent-security/).
**Fix:**
- For every client except the hosted crew, `read.external_text` returns only quarantined typed extracts (`std::agents::extract`, run server-side), never raw text.
- Raw reads need a per-client flag, `allow_raw_external`, set by `policy:admin`. It records the host's tool inventory and is never allowed on repositories above `internal`.
- Hosted-crew web access is quarantined: fetches run in a tool-free context and return typed extracts, and no URL may be built from context data.
- State the rule in the server instructions returned by `server/discover`.
- Add host-side exfiltration cases to O-AGT-8, using a reference host that has a fetch tool.

### R5-08 · Major · Targets: AGT
**Section:** AGT Data classes and model endpoints (D-AGT-19)
**Problem:** Clearance for external hosts attaches to the OAuth client identity, its Client ID Metadata Document URL, but that identity is not authenticated for native clients with localhost redirects. A malicious local program can present a cleared client's id. The identity also says nothing about which model or provider the host forwards content to, and a cleared IDE agent can switch providers in its settings.
**Evidence:** MCP: "Client ID Metadata Documents cannot prevent `localhost` URL impersonation by themselves." (https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations). The CIMD example uses `"token_endpoint_auth_method": "none"` (https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration). AGT: "clearance attaches to the OAuth client identity that the organization registers, meaning its Client ID Metadata Document URL".
**Fix:** Clearance above `internal` requires one of two setups:
- the hosted crew, or
- a pre-registered confidential client that authenticates with `private_key_jwt` from a hardware-backed key, with its model traffic routed through a Crucible model gateway. The gateway enforces the endpoint allowlist and records the model actually used.

`Declared` endpoints are never cleared for `confidential` or `export_controlled`. Add the error `label.client_unattested`.

### R5-09 · Major · Targets: ECO, PLT, KLN
**Section:** ECO Running on every platform; PLT Wasmtime configuration, Open questions (6); KLN Distributed and remote evaluation
**Problem:** Third-party evaluation components from verified publishers run inside the engine process. That process holds every open repository and the user's tokens and can use the device signing key, so Wasmtime is the only boundary. Wasmtime's 2026 advisories include an out-of-bounds write in Component Model string transcoding and data leakage between pooling-allocator instances, and PLT uses the pooling allocator. On servers, no tab requires separate worker processes per tenant or per label scope.
**Evidence:** ECO: "Evaluation-context Wasm components from verified publishers run in process for speed". PLT: "Pooling allocator sized from the memory budget". PLT open question 6 leaves engine sandboxing undecided. GHSA-394w-hwhg-8vgm "Out-of-bounds write or crash when transcoding component model strings" and GHSA-6wgr-89rj-399p "Data leakage between pooling allocator instances" (https://github.com/bytecodealliance/wasmtime/security/advisories).
**Fix:** (1) Only first-party, hermetically built components run in the engine process. Every third-party component runs in a worker process under the OS sandbox PLT already specifies for native plugins (AppContainer, App Sandbox, seccomp with Landlock), which answers PLT open question 6. (2) On servers, run one worker process per (tenant, label scope). `export_controlled` scopes get dedicated VMs, and pooling slots are never reused across tenants or scopes. (3) Apply Wasmtime security releases within 7 days on every supported line (D-PLT-21), gated by O-ECO-6.

### R5-10 · Major · Targets: ECO
**Section:** ECO Signing, provenance and transparency (D-ECO-16), Manifest and lockfile
**Problem:** Clients check that a package is Sigstore-signed, but they learn from the registry which identities may publish to a namespace. A compromised registry can therefore authorize its own identity and publish versions that every client accepts at the next update. ECO also overstates TUF: with online registry keys, TUF does not survive a compromise of the registry itself.
**Evidence:** ECO: "The Update Framework, which keeps update systems secure even when the repository or signing keys are compromised". PEP 458 says its online-key model "does not protect projects from attackers who have compromised PyPI" and leaves that to developer signing in PEP 480 (https://peps.python.org/pep-0458/). The ECO lockfile pins hashes and "the digest of the signature bundle", not the signer identity.
**Fix:** (1) Each namespace gets a trusted-publisher policy: an OIDC issuer and a subject pattern, such as repository and workflow. The namespace owner's offline key signs it as delegated TUF targets (the PEP 480 model), and every change is logged with notice to the owner. (2) The lockfile records each package's signer identity. `crucible update` treats a signer change like a capability escalation that needs human approval. (3) Organizations may run monitors of the registry log for their namespaces. (4) Reword the TUF row to state which compromises it survives.

### R5-11 · Major · Targets: ECO, KLN
**Section:** ECO Names and namespaces (D-ECO-13), Mirrors, private registries and air gaps; KLN Software supply chain
**Problem:** Domain claims and code-host organization claims produce names in one flat namespace with no precedence, and code-host organization names are first-come, so whoever registers a GitHub organization `acme` first can claim the namespace acme.com's owner needs. Maven Central, which ECO cites, avoids this with reverse-DNS names and an `io.github.` prefix that it grants only for personal usernames. KLN exempts verified publishers from the edit-distance typosquat block, while ECO holds all such names for review. A namespace missing from a deployment's private mapping silently resolves from the public registry.
**Evidence:** ECO: namespace claims "By domain ...; by code-hosting organization (OIDC from the host)". Maven Central domain namespaces "reuse the domain name system in a reversed manner"; code-host namespaces use `io.github.<username>`, "only for their personal username, not an organization name" (https://central.sonatype.org/register/namespace/). KLN: "blocks names within an edit distance of 1 from popular packages unless the publisher is verified".
**Fix:** (1) Domain claims own bare names. Code-host claims take a mandatory prefix (`gh_<org>`, `gl_<org>`) and can never collide with them. (2) Re-verification needs DNS control plus an existing publisher credential, so a lapsed and re-registered domain cannot take over a namespace. (3) Look-alike names are held for review whatever the publisher's status, and ECO adopts KLN's 72 h minimum age. (4) When an organization registry is configured, resolution defaults to deny for namespaces not on an allowlist. A lockfile entry whose registry changes fails resolution.

### R5-12 · Major · Targets: ECO, PLT
**Section:** ECO Running on every platform (D-ECO-10); PLT Formats per target, In the browser
**Problem:** In the browser, every component ships with registry-generated JavaScript glue that runs in the engine worker's origin, where it can reach OPFS (every local repository), authenticated `fetch` and WebCrypto keys; the glue, not Wasm, is the real boundary. The web app is served with HTTPS and SRI on an entry script that the same server controls. A compromised CDN or deployment can therefore serve arbitrary code to every browser user, including the approval page. Linux apt and dnf metadata is signed with OpenPGP but has no stated freshness bound.
**Evidence:** ECO D-ECO-10: the registry transpiles each component "into ES modules", as jco does. PLT: "Content-hashed static assets plus a service worker | HTTPS; Subresource Integrity on the entry script"; Linux: "Repository metadata signed with OpenPGP". TUF lists indefinite freeze and rollback among the attacks it addresses (https://theupdateframework.github.io/specification/latest/).
**Fix:** (1) Ship one first-party, generic component runtime (fixed JavaScript inside the app) that instantiates core modules from data, so the registry ships no per-component JavaScript. (2) Run third-party components in a separate cross-origin sandboxed worker or iframe with no OPFS or credentials, exchanging data by `postMessage`. (3) Publish each web release's asset manifest to a transparency log. The service worker verifies new versions against TUF targets before activating them, and enterprise mode serves assets from the verified offline bundle. (4) Give apt and dnf metadata a short expiry and have the updater enforce it.

### R5-13 · Major · Targets: AGT, ECO
**Section:** AGT Untrusted content is data (origins), Text descriptions; ECO The documentation system, Verified publishers
**Problem:** Text from verified publishers is treated as trusted: package READMEs, docs, description templates and catalog definitions. That gives instruction authority to anyone who passed a legal-identity check, and to anyone who compromises such a publisher's account or CI. Verification establishes who published, not that the text is safe to obey.
**Evidence:** AGT lists "Package READMEs and docs from unverified publishers" as untrusted, so verified ones are trusted. D-AGT-10 context: "Templates from unverified publishers are untrusted text". ECO: "A package's README is shown as `ExternalText` (AGT) unless the publisher is verified". ECO: a verified publisher has "legal identity checked by the marketplace operator".
**Fix:** Instruction authority comes only from three sources: the delegating human's goal, role skills whose manifest digest a `policy:admin` approved, and first-party std and `crucible::` documentation built by the hermetic builder. All third-party package text, verified or not, is `ExternalText`; verification changes badges, never integrity. Third-party description templates render as typed facts plus an `ExternalText` handle for the phrasing.

### R5-14 · Major · Targets: ECO
**Section:** ECO Contexts, Capability model
**Problem:** A connector may import `crucible:api` (design reads under its granted scopes) together with `wasi:http` to its declared hosts, and a tool component may combine `crucible:api` with filesystem writes and process spawning. A supplier connector granted both "read designs" and "send requests to api.supplier.com" is therefore an exfiltration channel. The plain-language grant shows two harmless sentences, not their combination, because the capability model has no rule on information flow.
**Evidence:** ECO contexts table: Connector may import "`crucible:api`, `wasi:http` to declared hosts"; Tool may import "`crucible:api`, `wasi:filesystem` on granted directories, ... `crucible:tool/process`". The grant example is "send requests to api.example-supplier.com".
**Fix:** A component may hold at most one of three capabilities unless `policy:admin` grants a named exception:
- reads of data labelled above `public` through `crucible:api`;
- network egress;
- filesystem writes outside CAS.

Connector API scopes narrow to their record types (`catalog:read`, offer writes) and never include `design:read`. An outbound request that carries data derived from labelled reads goes through the outbound Act pipeline (R5-06). Grant screens state the combination ("can read your designs and send data to api.supplier.com"). O-ECO-8 adds combined-capability exfiltration tests.

### R5-15 · Major · Targets: AGT, KLN
**Section:** AGT Data classes and model endpoints (D-AGT-19), Auto-merge policy; KLN Authorization, Export control
**Problem:** One person controls each of the most consequential settings. One administrator can clear a hosted model for `export_controlled` data, one `export_officer` can declassify, and one person approves a Cedar policy change. A malicious, coerced or phished administrator can export a whole ITAR program in a single action.
**Evidence:** AGT: "Every model endpoint carries a clearance per data class, granted by the organization's administrator". KLN: "Lowering a label requires a declassification record: a signed determination by a principal with the `export_officer` role". KLN Cedar analysis: "a person approves that list". KLN already requires two administrators for a purge.
**Fix:** Require two distinct humans for each of the following; for label-related items, one must hold `export_officer`:
- clearing any endpoint or recipient for `confidential` or `export_controlled`;
- declassification;
- Cedar changes that widen access;
- auto-merge policy;
- recipient-registry changes;
- oracle and protected-path changes.

Refuse policy Proposals from any context with untrusted data. Provide break-glass access with a mandatory review afterwards and an alert to every administrator.

### R5-16 · Major · Targets: UIX, PLT, KLN
**Section:** UIX Comments anchored to geometry, Notifications, Crash and error reporting; PLT Crash handling; KLN Export control
**Problem:** Label enforcement stops at the API, but labelled content leaves through channels that never consult labels: comment snapshots "for email and mobile", email digests, push notifications relayed by OS vendors, OS cloud backup or sync of the local CAS and journal, clipboard-history sync, crash minidumps whose stack memory may hold design data, and reproduction bundles containing the whole branch. Each sends content to a third party that holds the plaintext, which defeats ITAR's end-to-end condition. UIX's "Values and content are never recorded" also contradicts PLT's own statement about stack memory.
**Evidence:** UIX: `snapshot` is a "rendered still frame, for email and mobile"; "email digests are optional"; a reproduction bundle holds "branch, `api` call log and `ViewState`". PLT: "Stack memory can hold fragments of design data". 22 CFR 120.54(b)(1) requires that "the means of decryption are not provided to any third party" (https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54).
**Fix:** Add one label-aware egress rule to PLT and UIX. For labels above `internal`:
- Notifications and emails carry only ids and generic text, never snapshots or names; push payloads carry no content.
- Crash reports upload only the signature and module list.
- Reproduction bundles go only to the organization's own server.
- The CAS, journal and caches refuse to live in a cloud-synced folder and are marked excluded from OS backup.
- Copies of labelled content are excluded from clipboard history and cloud clipboard where the OS allows, and a policy can forbid copying.

Correct UIX's crash-reporting text to match PLT.

### R5-17 · Major · Targets: AGT, ECO, UIX
**Section:** AGT Rendered views and Field overlays; Untrusted content is data (instruction-capable content)
**Problem:** Images can carry instructions, and imported geometry or textures can depict text: embossed letters, or texture maps in glTF, 3MF or USD files. If label propagation applies, every render of an assembly with any supplier part is untrusted and taints every session that uses vision, which destroys utility and invites approval fatigue. If it does not apply, text-shaped geometry is an unmonitored injection channel. The draft does not say which.
**Evidence:** AGT: "Only free text and images can carry instructions"; "a render of a model containing an untrusted STEP name stays untrusted"; "The renderer never draws external strings: marks are numbers, and labels come from typed data", which covers labels but not geometry or textures.
**Fix:** A render is untrusted and instruction-capable when the geometry or appearance of any visible Body derives from an untrusted Asset. Agent renders default to `appearance: neutral`, which drops imported textures. Privileged contexts query untrusted renders only through a quarantined vision call with templated questions and typed answers: `inspect.ask_render { template, marks }` returns mark ids, booleans or counts. The scene graph, measurements and `inspect.describe` stay non-tainting. The injection suite adds embossed-text geometry and textured imports.

### R5-18 · Major · Targets: MFG, AGT
**Section:** MFG Approval and machine safety (D-MFG-4), Machine and MES connectivity (D-MFG-20), Printer profiles, 3MF and machine connectivity; AGT Role catalog (CAM programmer), Irreversible real-world actions
**Problem:** MFG says agents can never transfer programs and "a person triggers transfer", while AGT gives the CAM programmer the `send_to_machine` Act and lets the agent commit it after approval. MFG also exposes remote printer "start" and OPC UA writes as API actions. An approved plan, or a compromised approver, can therefore start motion on a machine nobody is standing at.
**Evidence:** MFG D-MFG-4: "agents can neither approve nor transfer programs"; MFG: "Send, start, pause, cancel, monitor through plugins ... as `api` actions"; AGT role table: CAM programmer, Act class `send_to_machine`. The EU Machinery Regulation "applies on a mandatory basis as of 20 January 2027" and "integrates provisions for cyber-safety for compliance-relevant software data and safety control systems" (https://single-market-economy.ec.europa.eu/sectors/mechanical-engineering/machinery_en).
**Fix:** Replace `send_to_machine` with `queue_program`, which delivers an approved, hash-bound program to the machine's DNC queue. An agent may prepare it, and a human approves it. Loading and cycle start happen only at the machine or gateway HMI with a person present, never remotely. OPC UA method calls are limited to reads and non-motion job management, and remote printer start is off by default. MFG and AGT state this one rule. The gateway signs as-run records.

### R5-19 · Major · Targets: CONTRACT, ECO
**Section:** contract §14 ruling ECO-5 and §13 phase 0 gate; ECO Trademarks
**Problem:** The ruling misses the most direct conflict. Siemens sells Simcenter Flux, an electromagnetic simulator for motors, sensors and actuators with motion and circuit coupling; that is the field of Crucible's physics engine. The ruling also treats Atlassian's conflict as ending in 2028, but Atlassian still lists Crucible in its trademark chart, and a mark does not lapse when product support ends. Operation names (`flux::…`) and namespaces (`crucible:`, `crucible::`) enter `OpKey`s, lockfiles and WIT packages, so renaming after behavior versions freeze breaks every pinned design.
**Evidence:** Simcenter Flux is "a leading electromagnetic simulation solution for designing and optimizing motors, sensors, actuators, and power devices" (https://www.siemens.com/en-us/products/simcenter/electromagnetics-simulation/flux/; altair.com/flux redirects there). Atlassian's trademark chart lists Crucible (https://www.atlassian.com/legal/trademark); new sales of Crucible ended 13 May 2025 and support ends 15 May 2028 (https://www.atlassian.com/software/crucible). Contract §14: "Crucible (Atlassian, until 2028)".
**Fix:** Rename the physics engine in phase 0 instead of holding a fallback name. For "Crucible", run a full clearance in the US, EU, UK, China and Japan for classes 9 and 42, on the assumption that Atlassian's mark persists. Make "names frozen" a precondition for freezing the first operation behavior version and the first `crucible:` WIT package. Correct the ruling text.

### R5-20 · Major · Targets: CONTRACT, KLN, ECO, PLT
**Section:** contract §7.7 (LTS); ECO Release channels, editions and long-term support; PLT Release channels and versions (D-PLT-27); KLN Deployment
**Problem:** LTS support is 24 months in the contract and PLT but 5 years in ECO. Either is short for aerospace, defence and medical programmes that qualify one tool version for a decade. A defence customer storing covered defense information in the cloud needs controls equivalent to FedRAMP Moderate, 72-hour incident reporting and forensic access from the provider, and no deployment mode offers them. A medical customer will validate Crucible under FDA's final Computer Software Assurance guidance and needs the vendor's evidence packaged for that.
**Evidence:** DFARS 252.204-7012(b)(2)(ii)(D) requires cloud providers to meet "security requirements equivalent to" the "FedRAMP Moderate baseline". The clause defines "Rapidly report" as "within 72 hours", requires images to be kept "for at least 90 days", and gives DoD access for forensic analysis under paragraph (f) (https://www.acquisition.gov/dfars/252.204-7012-safeguarding-covered-defense-information-and-cyber-incident-reporting.). FDA's CSA guidance is final, dated September 2025 (https://www.fda.gov/regulatory-information/search-fda-guidance-documents/computer-software-assurance-production-and-quality-system-software). Wasmtime LTS releases are supported for 24 months (https://docs.wasmtime.dev/stability-release.html).
**Fix:**
- Contract §7.7: standard LTS lasts 24 months. Add "regulated extended support": one LTS line every two years is supported for 10 years, with security backports by the steward or retired engines run in sandboxed processes (PLT open question 5). ECO adopts the same rule.
- KLN adds a "regulated cloud" deployment mode: US-only regions; US-person operations staff for ITAR tenants; controls mapped to NIST SP 800-171 with evidence of FedRAMP Moderate equivalence; and support for DFARS 7012(c) to (g) (help with 72-hour reporting, 90-day image retention, forensic access).
- Ship a CSA package: intended use and risk tier per capability, vendor oracle evidence, release impact notes, a supplier quality agreement template and audit rights.

### R5-21 · Major · Targets: KLN, AGT
**Section:** KLN Electronic signatures (21 CFR Part 11 table), Garbage collection (D-KLN-18), Encryption at rest; AGT Irreversible real-world actions
**Problem:** The Part 11 mapping omits 11.10(b) (complete copies for FDA review), 11.10(c) (retrieval throughout the retention period, which purge and crypto-shredding can break), 11.10(i) and (k) (personnel qualification and control of system documentation), and 11.30, which arguably covers the cloud service because the vendor controls access. AGT's release-Act approvals are not tied to KLN signature records, so a release can carry an approval without the 11.50 manifestation. The QMSR sentence limits design controls to class II and III devices, but 820.10(c) also covers class I devices automated with computer software and five listed class I types.
**Evidence:** 11.10(b): "The ability to generate accurate and complete copies of records in both human readable and electronic form"; 11.10(c): "Protection of records to enable their accurate and ready retrieval throughout the records retention period"; an open system is one where "system access is not controlled by persons who are responsible for the content of electronic records" (https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-11). For 820.10(c), see https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820/subpart-B/section-820.10. KLN: "Deleting a domain key destroys every object of that domain at once (crypto-shredding)".
**Fix:** Add these rows:
- 11.10(b): export signed records with their signatures as PDF/A plus JSON, with an offline verifier.
- 11.10(c): retention locks, so records under a Part 11 policy cannot be purged or crypto-shredded before retention ends without a documented two-person deviation.
- 11.10(i) and (k): vendor training records, and controlled release documentation with change notices.
- 11.30: cloud mode is treated as an open system, with the encryption and signature controls that apply listed.

Every AGT approval of a release or R4 Act becomes a KLN signature record with meaning, printed name and time. Correct the QMSR scope sentence to cite 820.10(c).

### R5-22 · Major · Targets: ECO, PLT
**Section:** ECO Security disclosure, License; PLT Software bill of materials and provenance
**Problem:** Crucible has no export classification of its own, although its commercial binaries and hosted service contain cryptography, and publicly available encryption source code that uses non-standard cryptography needs an email notification to BIS and NSA. Under the Cyber Resilience Act, the company will be a manufacturer, with SBOM and vulnerability-reporting duties, and the later foundation an open-source software steward. ECO's disclosure policy is a 90-day embargo with no CRA reporting path. PLT leaves the SBOM question "not verified" although the CRA's recitals presuppose one.
**Evidence:** 15 CFR 742.15(b) requires notifying "crypt@bis.doc.gov" and "enc@nsa.gov" for non-standard cryptography (https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-742/section-742.15). CRA recital 22 refers to SBOMs manufacturers "have generated pursuant to this Regulation"; recital 65 says manufacturers "notify simultaneously via the single reporting platform"; recital 19 gives stewards a "light-touch and tailor-made regulatory regime" (https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402847). PLT: "whether its text mandates an SBOM was not verified".
**Fix:** ECO adds an "Export classification" section. It classifies each distributable (open-source code, commercial binaries, hosted service, first-party packages) under the EAR and the EU dual-use regime, sends the crypto notification if non-standard cryptography is ever used, and publishes classification statements for customers. The disclosure policy adds the CRA path: an actively exploited vulnerability starts the 24-hour early warning and 72-hour notification through the single reporting platform, whatever the embargo. The company is the manufacturer for commercial distributions; the foundation becomes the steward after transfer. PLT deletes its "not verified" note.

### R5-23 · Major · Targets: KLN, ECO, PLT
**Section:** KLN Electronic signatures, Tamper-evident audit; ECO Signing, provenance and transparency; PLT Signed delta updates
**Problem:** Release tags, transparency checkpoints, provenance, TUF metadata and Part 11 signatures use only ECDSA P-256 or Ed25519. These records must verify for decades, and US national-security customers will need post-quantum signatures soon. Hashes reserve an algorithm byte; signatures have no agility and no migration plan.
**Evidence:** KLN: "an ECDSA P-256 signature from the signer's hardware-backed key"; checkpoints "carry an Ed25519 signature". FIPS 204 (ML-DSA) became final on 13 August 2024 (https://csrc.nist.gov/pubs/fips/204/final). The CNSA 2.0 FAQ: from 1 January 2027 "New NSS acquisitions must be CNSA 2.0 compliant"; LMS and XMSS are approved, and ML-DSA-87 is approved for all classification levels (https://media.defense.gov/2022/Sep/07/2003071836/-1/-1/0/CSI_CNSA_2.0_FAQ_.PDF).
**Fix:** Every signature record carries an algorithm id. By phase 2, release tags, the TUF root and targets, checkpoints and provenance are dual-signed: the current algorithm plus ML-DSA-87, or plus LMS for release signing. Long-retention records are re-timestamped periodically into an evidence chain, so they still verify after an algorithm is retired. Add hybrid post-quantum key exchange to TLS once the FIPS provider supports it, and define a CNSA 2.0 deployment profile.

### R5-24 · Major · Targets: ECO
**Section:** ECO Marketplace (Verified publishers; Paid packages, D-ECO-19), Open questions (7)
**Problem:** The marketplace sells and delivers software worldwide with no sanctions screening of publishers or buyers, no export-classification field on packages, and no rule keeping `export_controlled` content off the public registry. Escrow rights "for their own use" have no three-party agreement behind them. Binary-only paid packages also escape the licence, secret and malware scanning that source code allows.
**Evidence:** ECO: "Paid packages may ship as compiled Wasm components only"; escrow "[unverified: legal enforceability per jurisdiction]"; open question 7 defers export control until "before paid packages open".
**Fix:**
- Verified publishers pass know-your-business checks with restricted-party screening.
- Purchases are screened, and comprehensively sanctioned jurisdictions are geo-restricted.
- Paid packages must declare a manifest field `export_classification` (ECCN, EAR99 or "not subject", with the basis).
- The registry refuses to publish any package that carries `export_controlled` labels.
- Escrow runs through an independent agent under a published beneficiary agreement, and the registry scans escrowed source privately for licences, secrets and malware before listing.

### R5-25 · Major · Targets: ECO
**Section:** ECO Stewardship (D-ECO-22), Teams and decisions, Marketplace
**Problem:** The foundation commitment is a charter sentence, not an enforceable obligation. Its trigger can slip indefinitely, because phase gates have no dates and the company employs most maintainers. After transfer, the foundation would hold the registry's namespace authority while the company runs the marketplace, paid-package delivery and badges on the same registry. That is a conflict of interest, and nothing says who holds the TUF root or the trust roots.
**Evidence:** ECO: "The trigger is the earlier of the phase 3 gate or the first 12-month period in which at least three organizations other than the company employ active maintainers. The commitment is written in the project charter at phase 0." ECO: "The company keeps what it builds on top: hosted services, the marketplace operation".
**Fix:** Create a foundation, or join an umbrella foundation, at phase 0 to hold the trademarks and namespace authority, with the company as operator under a revocable service agreement. If the trigger stays, add a backstop of "no later than 36 months after the first stable release" and make it binding, for example through a covenant with an independent party or an escrowed trademark assignment. A key ceremony places the TUF root and namespace-policy keys with keyholders of whom at least half are not company employees. Marketplace ranking and badge rules are published foundation policy, and the company receives a trademark licence for its hosted services.

### R5-26 · Major · Targets: ECO
**Section:** ECO Contributions (D-ECO-21)
**Problem:** Under the DCO, the signer certifies that the work "was created in whole or in part by me", or that the earlier work it builds on is under an appropriate open-source licence "to the best of my knowledge". A human signing off on agent output cannot know whether it reproduces copyleft code. ECO accepts agent contributions with only a provenance trailer, so the Apache-2.0 core can absorb GPL-derived code.
**Evidence:** DCO 1.1 (https://developercertificate.org/). The Linux Foundation's generative-AI policy asks contributors to confirm that the AI tool's terms do not conflict with the project licence and that any third-party material in the output is licensed and attributed (https://www.linuxfoundation.org/legal/generative-ai). ECO: "The human principal on whose behalf the agent acted signs off".
**Fix:** Publish an AI-contribution policy:
- Agents never add `Signed-off-by`, and an `Assisted-by: <tool, model>` trailer is mandatory.
- The human's sign-off certifies review plus the Linux Foundation conditions.
- Agent-authored diffs over 50 lines run a code-similarity scan against known copyleft corpora, and a match blocks merge.
- `ChangeProvenance` is mirrored into the public history.
- Area teams may require a human reimplementation in determinism-critical crates (`detmath`, `kernels`, `anvil-*`).

### R5-27 · Major · Targets: KLN, AGT, UIX
**Section:** KLN Tamper-evident audit (D-KLN-30), Electronic signatures; AGT Audit, Provenance of agent changes; UIX Approvals, Presence
**Problem:** Transparency logs are append-only and never pruned without a retention policy; signature records carry printed names; audit records, transcripts and API logs carry principal identities for seven years by default; and the UI records which tabs each approver viewed. None of this personal data has an erasure or minimization design. Per-person activity records (presence, follow mode, viewed tabs) are monitoring that needs works-council agreement in Germany, which blocks deployment for EU customers until it is configurable.
**Evidence:** KLN: "Logs are never pruned without a retention policy". AGT: "a default of seven years for repositories that contain releases [unverified ...]". UIX: "The UI records which tabs were viewed as part of the approval". GDPR Art. 17(3)(b) and (e) permit retention for legal obligations and legal claims (https://gdpr-info.eu/art-17-gdpr/). German Works Constitution Act §87(1) item 6 gives co-determination over "the introduction and use of technical devices designed to monitor the behaviour or performance of the employees" (https://www.gesetze-im-internet.de/englisch_betrvg/englisch_betrvg.html).
**Fix:**
- Logs and records hold pseudonymous principal ids. A separate identity directory maps ids to names under a per-person key that can be crypto-shredded, except under documented legal holds (Part 11 retention, litigation).
- Transcripts and API logs get their own retention, 12 months by default, separate from release records.
- Presence, follow mode and tab-view recording are organization settings, with a works-council mode that disables per-person activity analytics.
- Ship records-of-processing entries and a DPIA template.
- List hosted model providers as sub-processors, with their regions and retention terms.

### R5-28 · Major · Targets: AGT
**Section:** AGT Customer data (D-AGT-22)
**Problem:** The opt-in to "improving the crew for everyone" trains a shared model on scrubbed corpora that keep "geometry, Ingot structure and edit patterns", which for a design company is the intellectual property itself, and such a model can reproduce training items to other tenants. Eligibility ignores `DataLicence` and confidentiality labels; only `export_controlled` is excluded. Supplier models under NDA and licensed catalog geometry can therefore enter the corpus. After withdrawal, trained weights stay in service until the next scheduled retraining.
**Evidence:** AGT: "Scrubbing. Names, comments and external text are removed or replaced before training, keeping geometry, Ingot structure and edit patterns"; "Never eligible: `export_controlled` repositories, under any setting"; "Models trained on it are not redistributed beyond the next scheduled retraining."
**Fix:**
- Cross-tenant training admits only items labelled `public`, or whose `DataLicence` explicitly permits ML training under a contract addendum. It never admits `confidential` items or third-party Assets.
- Per-tenant adaptation uses dedicated weights that are never served to other tenants.
- Before any shared model ships, deduplicate the corpus and run canary-extraction tests: planted canaries must not be reproducible.
- Eligibility is computed per item from its labels.
- Withdrawal takes affected shared models out of service within 30 days.

### R5-29 · Major · Targets: UIX, PLT
**Section:** UIX Telemetry (D-UIX-22), Crash and error reporting; PLT Opt-in performance telemetry, Enterprise policy
**Problem:** There are two telemetry pipelines with different payloads, identifiers and retention: UIX keeps raw events for 90 days and sends command ids, error codes and settings, while PLT uses a random install id, drops aggregates covering fewer than 50 installs, and keeps data for 13 months. Neither names a controller, legal basis, processors, storage region or transfer mechanism, although install ids and IP addresses are personal data. UIX's "air-gapped builds exclude the sender at compile time" contradicts PLT's single reproducible binary per architecture.
**Evidence:** UIX: "Raw events are kept 90 days; aggregates are kept longer". PLT: "a random install id that resets on request"; the server "retains data for 13 months". GDPR Recital 30: persons "may be associated with online identifiers provided by their devices, applications, tools and protocols", such as IP addresses (https://gdpr-info.eu/recitals/no-30/).
**Fix:** One pipeline, owned by PLT, with one public schema: the union of the UIX and PLT fields, minus raw command streams.
- Telemetry is opt-in per install.
- The install id rotates every 90 days and is never joined to account ids.
- The server drops aggregates covering fewer than 50 installs.
- Raw data is kept for 90 days and aggregates for 13 months.
- EU organizations' data is collected in an EU region.
- A privacy notice names the steward as controller, plus the processors and the transfer basis, and a DPIA template ships with it.

Replace compile-time exclusion with the signed enterprise policy `telemetry.performance = off` plus an egress allowlist.

### R5-30 · Major · Targets: KLN, AGT
**Section:** KLN Threat model; AGT Taint and the Rule of Two, State of the art (prompt-injection row)
**Problem:** The two threat models contradict each other on their central claims. KLN says the defence follows "CaMeL's separation of control flow from data" and that no agent session holds all three trifecta properties. AGT explicitly rejects a CaMeL interpreter and says a tainted session "holds all three of the Rule of Two's properties". Customers' security reviewers will read KLN's stronger claim, which is wrong.
**Evidence:** KLN threat model rows "Prompt injection through model content" ("following CaMeL's separation of control flow from data") and "Lethal trifecta" ("No agent session holds all three"). AGT: "Deviation: no CaMeL interpreter around every role. *Reason: maturity.*" AGT: "A tainted session holds all three of the Rule of Two's properties, but only in a narrow form".
**Fix:** Say it once. KLN states the consequence in one line and points to AGT: "Agents follow AGT's label and taint model; tainted sessions hold all three Rule of Two properties in a narrow form and are supervised by review and Act approval." Remove the CaMeL attribution from KLN.

### R5-31 · Minor · Targets: CONTRACT, ANV, MFG, ECO
**Section:** contract §7.1 (Anvil); ANV GPU strategy and freedom to operate; MFG Toolpath algorithms (D-MFG-7); ECO Yanking, deprecation and removal
**Problem:** The contract calls US 12,229,885 B1 "Zoo's patent", but Google Patents lists the inventor as Alyn Rockwood and the assignee as "Individual". The freedom-to-operate review must name the right owner and cover pending continuations. Claim 1 is a method claim with no parallel processor (only system claim 6 has one), so a CPU sampling path is also in scope. The search for Boeing's US 9,164,503 did not cover other CAM vendors' constant-engagement patent families, and the registry has no path for removing content over a patent claim.
**Evidence:** Google Patents lists the current assignee of US 12,229,885 B1 as "Individual", and system claim 6 recites "a parallel computing processor" (https://patents.google.com/patent/US12229885B1/en). Claim 1 of US 9,164,503 (assignee Boeing) requires a pre-roughing slot plus "curves spiraling outward from the pre-roughing slot" (https://patents.google.com/patent/US9164503B2/en).
**Fix:** The contract reads "the SSI patent US 12,229,885 B1 (inventor Alyn Rockwood, cited by Zoo)". The ANV and MFG freedom-to-operate briefs cover the CPU path, continuations and the main CAM vendors' engagement-control patents. ECO's "Legal removal" row adds patent notices, with counter-notice and transparency-log entries.

### R5-32 · Minor · Targets: CONTRACT, ECO
**Section:** contract §7.7 (Licensing); ECO License (D-ECO-20)
**Problem:** "MPL-2.0 (unmodified, or with changes published upstream)" misstates the obligation. MPL §3.2(a) requires the Source Code Form to be available for every Executable distribution, modified or not, and browser bundles count. ECO marks MPL's patent-retaliation terms as unverified, but §5.2 contains them. "GPL code runs only as an external tool" omits the source obligation that arises when Crucible distributes GPL container images to on-premises customers.
**Evidence:** MPL-2.0 §3.2(a): "such Covered Software must also be made available in Source Code Form"; §5.2 ends the patent licence of a party that starts patent litigation (https://www.mozilla.org/en-US/MPL/2.0/).
**Fix:** Contract: "MPL-2.0 files may be linked; every distribution (native, Wasm, browser bundle, container) ships MPL notices and a source offer for each MPL file; modifications are published under MPL-2.0." Add: "Distributed GPL or AGPL container images ship with their corresponding-source offer." ECO's comparison table records MPL §5.2.

### R5-33 · Minor · Targets: ECO, AGT
**Section:** ECO Reconstruction: geometry to features; AGT Licensing constraints (D-AGT-22)
**Problem:** Reconstruction relies on BRepNet, whose published results come from the Fusion 360 Gallery segmentation dataset. That dataset is licensed only for non-commercial research. Shipping weights trained on it, or fine-tuned from such weights, would breach the licence, and D-AGT-22's exclusion is written only for agent training.
**Evidence:** ECO: BRepNet "outperforms mesh and point-cloud methods on the Fusion 360 Gallery segmentation dataset". The licence allows use "only for non-commercial research purposes", and Autodesk may terminate it at any time (https://github.com/AutodeskAILab/Fusion360GalleryDataset/blob/master/LICENSE.md).
**Fix:** Extend D-AGT-22 to every shipped model, in every tab. ECO trains its segmentation models on Crucible's procedural corpus and on data with verified commercial licences. It may cite BRepNet's architecture and benchmark against Fusion 360 Gallery only in non-shipping research.

### R5-34 · Minor · Targets: MFG
**Section:** MFG RoHS, REACH and conflict minerals
**Problem:** The table treats Regulation (EU) 2017/821 as a product compliance check, but it applies directly only to EU importers of tin, tantalum, tungsten and gold minerals and metals. Finished products, and companies past the metal stage, carry no obligations under it. A `NonCompliant` verdict under that regulation would be legally wrong. The RoHS row (ten substances) and the REACH row are correct.
**Evidence:** The Commission: the regulation "will only apply directly to EU-based importers of tin, tantalum, tungsten and gold" (https://policy.trade.ec.europa.eu/development-and-sustainability/conflict-minerals-regulation/regulation-explained_en).
**Fix:** Reword the row as "3TG sourcing data (smelter lists, due-diligence evidence) collected for customers' and importers' reporting". It produces a data-completeness Check, not a compliance verdict.

### R5-35 · Minor · Targets: MFG
**Section:** MFG EU Digital Product Passport (D-MFG-21)
**Problem:** The implementing-regulation and implementing-decision numbers and the delegated-act timetable come from a vendor blog, not from EUR-Lex. The design also omits the ESPR back-up copy that the economic operator must keep with an independent third-party DPP service provider.
**Evidence:** The Commission's news item confirms that the registry launched on 20 July 2026 and accepts registration through "a web interface or an API" (https://transition-pathways.europa.eu/retail/news/digital-product-passport-registry-now-live). ESPR recital 38 requires a back-up copy "through a digital product passport service provider that is an independent third party" (https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202401781).
**Fix:** Cite EUR-Lex for the act numbers or mark them [unverified]. Add a capability, "Back-up copy", that mirrors each published passport to a second, independent DPP service provider named in the delegated-act package, with its failure behavior and oracle.

### R5-36 · Minor · Targets: AGT, KLN
**Section:** AGT Data classes and model endpoints; KLN Export control
**Problem:** AGT's summary of the ITAR carve-out omits two conditions. 120.54(a)(5)(v) requires that the data not be sent from a §126.1 country. 120.54(b)(2) requires the intended recipient to be the originator, a U.S. person in the United States, or a person otherwise authorized. KLN's "even visual inspection" paraphrase drops the qualifier "of a defense article that reveals technical data".
**Evidence:** 22 CFR 120.54 (https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54); 22 CFR 120.56(a)(1) (https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.56).
**Fix:** Add both conditions to AGT's summary. KLN's end-to-end mode checks recipient eligibility (U.S. person, or otherwise authorized) before it releases a key to a client. KLN quotes 120.56 exactly.

### R5-37 · Minor · Targets: AGT
**Section:** AGT Sessions, identity and delegation; The Proposal object
**Problem:** AGT adopts RFC 8693 semantics ("the outermost actor is current"), then defines `Proposal.delegation` as "outermost first: the human who started the work", the opposite order. Separation-of-duties checks depend on the order. RFC 8693 also makes nested actors informational only, so the chain must not come from token claims.
**Evidence:** AGT: "the outermost actor is current and nested actors are prior"; `delegation: Vec<Principal>, // outermost first: the human who started the work`. RFC 8693 §4.1: "Prior actors identified by any nested act claims are informational only" (https://www.rfc-editor.org/rfc/rfc8693.html).
**Fix:** Define one order: `delegation: Vec<Principal> // index 0 = delegating human, last = current actor`. Derive it from server-side session lineage (`work_item` to parent session), never from token `act` claims. O-AGT-7 tests separation of duties on chains of depth 1 to 3.

### R5-38 · Minor · Targets: AGT
**Section:** AGT MCP profile (HTTP headers)
**Problem:** Mirroring the `repo` argument into an `Mcp-Param-Repo` header exposes repository names to every proxy, WAF and log on the path. Repository names often reveal programmes, for example "f47-wing-itar".
**Evidence:** MCP: "Server developers **SHOULD NOT** mark sensitive parameters (passwords, API keys, tokens, PII) with `x-mcp-header`, as header values are visible to network intermediaries." (https://modelcontextprotocol.io/specification/2026-07-28/server/tools).
**Fix:** Add a `shard_key` argument, HMAC-SHA-256(tenant routing key, repository id) truncated to 16 bytes, and mirror that into the header instead of the repository name.

### R5-39 · Minor · Targets: AGT, KLN
**Section:** AGT Audit; KLN Tamper-evident audit (D-KLN-30)
**Problem:** There are two audit logs: AGT's hash chain anchored in the repository hourly, and KLN's per-tenant tlog-tiles logs with witnesses. Their retention rules also differ: seven years (unverified) against "the longest record retention the organization configures". An auditor must reconcile two integrity mechanisms.
**Evidence:** AGT: "Records are append-only and form a hash chain, whose head is signed and anchored in the repository every hour". KLN D-KLN-30.
**Fix:** AGT audit records become entries in KLN's transparency log, with one retention rule (KLN's) and one verifier. AGT keeps only the record schema.

### R5-40 · Minor · Targets: KLN, ECO
**Section:** KLN Secure supplier collaboration (watermarks); ECO Deterministic export
**Problem:** Per-recipient watermarks change file bytes, so a supplier's file no longer matches the SHA-256 in the signed release manifest. Nobody can then prove which release a returned or leaked file came from.
**Evidence:** KLN: "Each file is watermarked per recipient: visibly where the format allows, and by a recipient fingerprint in metadata". ECO: "A release lists its exported Files with their SHA-256 in the release manifest".
**Fix:** Make watermarking a recorded, deterministic transform. The data-package record stores the release file hash, recipient id, watermark parameters and recipient file hash, and a verifier recomputes the transform to tie any recipient file to its release.

### R5-41 · Minor · Targets: KLN
**Section:** KLN IP protection (D-KLN-31)
**Problem:** A remote parametric model returns Bodies for any parameter values, so a recipient can sample the parameter space and reconstruct the design intent the share was meant to protect. No quota, range limit or audit rule bounds this.
**Evidence:** KLN: "A feature callable with parameters; evaluation runs on the owner's workers, and results return as Bodies".
**Fix:** Each remote parametric share declares per-recipient query budgets, allowed parameter ranges and step sizes, and optional output simplification within a declared deviation. Every query is audited. A query over budget returns `ShareQuotaExceeded`.

### R5-42 · Minor · Targets: UIX, ECO
**Section:** UIX Extending the interface (D-UIX-23); What the toolkit requires from the platform layer (deep links)
**Problem:** Panel components can render element trees that imitate Crucible's own dialogs, such as a fake "session expired" prompt. Their `api/edit` calls appear in history as the user's own edits. URL-scheme deep links let any web page or agent message open in-app views, including approval pages.
**Evidence:** UIX: panels return "stacks, grids, text, fields, tables, charts, trees and viewport overlays"; `crucible:api/edit` is granted "only when the user grants it to this package". UIX's platform requirements list "URL-scheme deep links".
**Fix:** Panels render inside chrome that shows the package identity and may not use modal or system-styled elements. Panel edits record the package in `ChangeProvenance`, as agent edits do. Deep links navigate and never act; approval pages are reachable only from the inbox (R5-04).

### R5-43 · Minor · Targets: UIX, AGT
**Section:** UIX Steering mid-task, Comments anchored to geometry (@mentions), Agent panel (attachments)
**Problem:** UIX does not say who may steer a running agent or @mention it into action. Request attachments (comments, files) enter as part of the goal, which AGT treats as trusted. A collaborator, or a supplier's principal on a shared branch, could therefore instruct an agent with the delegating human's authority.
**Evidence:** UIX: "A message sent while an agent runs is delivered at its next step boundary as a priority instruction"; threads support "@mentions of people and agents"; the request input takes attachments including "comments, files". AGT trusts "The goal text from the delegating human."
**Fix:** Only the delegating human can steer. An @mention by anyone else creates a request in the delegating human's inbox. Attachments enter the agent's context as `ExternalText` with their origin, never as goal text.

### R5-44 · Minor · Targets: AGT
**Section:** AGT Model independence (D-AGT-21), Qualification and graceful degradation
**Problem:** Endpoint records name a provider and model id "if known", but local endpoints load weights from files, which are a supply-chain input that can be backdoored or swapped. Qualification is not bound to the weights actually served.
**Evidence:** AGT: `endpoint: Option<EndpointRecord>, // provider, model id, version if known, region`.
**Fix:** `EndpointRecord` pins the weights digest for local endpoints, or the provider's dated model version for hosted ones, and qualification records bind to it. A digest change forces re-qualification and is audited. Weights distributed through the registry are signed like packages.

### R5-45 · Minor · Targets: AGT
**Section:** AGT Sessions, identity and delegation (hosted crew token exchange)
**Problem:** The hosted crew mints downscoped tokens for every delegating human by token exchange. Compromising `apps/crew` therefore yields agent-level authority over every user who ever delegated.
**Evidence:** AGT: "The hosted crew mints one downscoped token per worker by token exchange [S47]."
**Fix:** A delegation is an explicit, signed, time-bound grant that the human creates (scope, repository, budget, expiry). The authorization server lets the crew exchange tokens only against a live grant and only for agent scopes. Tokens are sender-constrained (DPoP or mTLS), and crew instances run per tenant. Approvals and `policy:admin` can never be obtained by exchange.

### R5-46 · Minor · Targets: AGT
**Section:** AGT MCP profile; Built-in roles (skills)
**Problem:** Roles depend on the Skills extension, but the official Rust SDK's README claims support for 2026-07-28, Tasks and MRTR and does not mention Skills. The Skills extension also requires hosts to treat skill content as untrusted. AGT treats pinned role skills as trusted origins without saying that this trust is Crucible's own policy, not a protocol property.
**Evidence:** The rmcp README (https://github.com/modelcontextprotocol/rust-sdk). The Skills extension says "Treat skill content as untrusted input" and "Digests establish consistency with the server's manifest, not trust in its content" (https://modelcontextprotocol.io/extensions/skills/overview).
**Fix:** `apps/mcp` implements `skills/list`, `skills/get` and the manifests itself, with a conformance test in O-AGT-1. AGT states that role skills are trusted only by Crucible's hosted crew after `policy:admin` approval; external hosts apply their own policy.
