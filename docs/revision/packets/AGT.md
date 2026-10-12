# AGT round 4 packet

Your tab is `docs/spec/09-agents.md` at v3 (tag `round-3`). Round 4 fixes, in one pass: the 53 third-review findings that target it (5 Critical, 30 Major, 18 Minor), its 0 `[unverified]` claims, its open questions and the known items below. Contract v7 is binding; its section 18 lists the rulings on this review, and many findings below are already settled there.

## Third-review findings

### R15-02 · Critical · Targets: CONTRACT, KLN, AGT, ING
**Section:** Contract 5 `Labels` (integrity part), 7.6 "Free text is never endorsed by merging"; KLN "Memo entries and backdating", "Labels and export control"; AGT D-AGT-16 and AGT-O-14; ING "Free text"
**Problem:** Integrity is part of the node label and joins through every derivation, while free-text integrity enters at the node that evaluates the string. A Body or Part node holds geometry and names in one value, so a merged supplier STEP file whose names stay untrusted gives its Body node an untrusted label, and every mass, stress, BOM and drawing node downstream inherits it. Any agent that reads those results becomes `data_untrusted`, so every change is at least R2 and never auto-merges. AGT promises the opposite, so its oracle cannot pass against KLN's mechanism.
**Evidence:** Contract 7.6: "Every value evaluated from a free-text span … carries the span's integrity into its node's label." KLN: "A node's label is the join of its inputs' labels." AGT line 772: "A merged supplier STEP file thus yields trusted geometry and untrusted names". AGT-O-14: "a clean R1-shaped change on an assembly with a merged supplier part is R1". A node has one label, so it cannot be trusted for geometry and untrusted for names.
**Fix:** Track free-text integrity on values, not nodes. Ingot already has the type: a string evaluated from an untrusted span is an `ExternalText` value carrying its span's integrity, and `String` values are trusted by construction. `api` returns `ExternalText` values as handles wherever they appear, and node labels keep only confidentiality plus the integrity of typed inputs from unmerged pins. Delete the clause "carries the span's integrity into its node's label" from contract 7.6, KLN and ING, and change D-ING-24 to "values evaluated from free text are `ExternalText`". AGT-O-14 then holds by construction, and the instruction-capable Snapshot rule reads "any visible text derived from an `ExternalText` value".

### R15-05 · Major · Targets: CONTRACT, KLN, AGT, MFG
**Section:** Contract 2 (Waiver, Act), 7.6; KLN "Change orders" (Deviation), "Traceability and compliance" (exemptions); AGT "Acts and approvals"
**Problem:** Four records accept a departure under signature: a Waiver (a `CheckId`, Items, effectivity, reason, expiry), a Deviation ("a temporary departure for given serials or lots, with expiry"), a compliance exemption "signed by `quality`", and a policy allowance. The first three have the same shape. Deviations are granted by `grant_deviation`, an Act, although an Act is defined as "an effect outside Crucible" and AGT files it under the `Record` family with `release` and `yank_package`. Compliance also keeps its own verdict enum (`Compliant`, `NonCompliant`, `Unknown`) beside `CheckOutcome`.
**Evidence:** Contract 2 Waiver: "naming a `CheckId`, the Items and effectivity it covers, a reason and an expiry (a revision, a serial range or a date…)". KLN: "Deviation | A temporary departure for given serials or lots, with expiry, granted by the `grant_deviation` Act"; "exemptions signed by `quality`, and verdicts per revision (`Compliant`, `NonCompliant`, `Unknown`)". AGT: "`grant_deviation` | Record | A deviation against a release".
**Fix:** One Waiver record. A deviation is a Waiver whose effectivity is a serial or lot range against a released revision (MFG's conformance checks are what it waives); a compliance exemption is a Waiver of a compliance check by a principal with the `quality` role. Compliance checks return `CheckOutcome` (`Undecided { MissingData }` for "Unknown"). Redefine Act as "an API method whose effect needs a human Approval of an exact plan", which matches the `Record` family, and drop `grant_deviation` as an Act class.

### R15-06 · Major · Targets: CONTRACT, KLN, COV, AGT
**Section:** Contract 5 `Labels` (confidentiality part), 7.8 (encryption domains); KLN "Encryption at rest", "Shared cache and remote evaluation"
**Problem:** `licences` sits in the confidentiality lattice, and that lattice keys encryption domains, worker processes and live replication. Every `Material` carries a `DataLicence` that joins into every Field derived from it, so a design using materials from several licensed databases splits into one encryption domain, one worker process and no deduplication per combination of licences. A licence mostly restricts redistribution, which `release_data` already checks at exits; it rarely restricts who may read inside the tenant.
**Evidence:** Contract 5: confidentiality is "`{ level, controls, scopes, licences }`"; 7.8: "Encryption domains are keyed by tenant and canonical confidentiality label; deduplication never crosses them". KLN: "each worker process serves one (tenant, confidentiality label)". KLN `release_data` "refuses … one whose `DataLicence` forbids redistribution to that recipient".
**Fix:** Move `licences` out of the confidentiality part into a third label part, usage, joined through Kiln like the others but compared only at exits (`release_data`, exports, registry publish) and never used for encryption domains, worker partitioning or replication. A licence that does restrict reading maps to an organization `scope`, which stays in confidentiality.

### R15-15 · Major · Targets: CONTRACT, KLN, AGT
**Section:** Contract 5 (`ControlAuthorization`, policy allowance), 7.6 (write-down, approval credentials, standing releases), 7.8 (egress grants); KLN D-KLN-18, D-KLN-41, "Electronic signatures"; AGT "Acts and approvals"
**Problem:** Crucible has about a dozen kinds of human-signed record (Approval, Waiver, endorsement, declassification, `ControlAuthorization`, policy allowance, purge, recipient-record change, standing release, egress grant, envelope approval, review verdict), and the rules for who may sign each (how many people, which role, which credential level, whether the author or an agent may sign) are prose in contract 5, 7.6 and 7.8, KLN D-KLN-41, D-KLN-18 and AGT. KLN already has one signature record with a `meaning`, so the variety is in the rules, not the data.
**Evidence:** Contract 7.6: "a declassification record signed by two people, one of them an export officer"; "A `standing_release` is approved by two humans"; "Export-officer actions, physical-effect Acts … need AAL3". Contract 5: `ControlAuthorization` "created by an export officer with a second person"; allowance "with two signers". 7.8: "a two-person grant". KLN D-KLN-41 lists eleven items.
**Fix:** One table in contract 5, "Signature meanings": meaning · subject type · signers required · roles · credential level · author may sign · agent may sign. Every two-person, AAL3 and no-self-approval rule becomes a row, Cedar evaluates it, and KLN-O-POLICY-1 fuzzes the table. Delete the scattered prose and D-KLN-41's list in favour of the table.

### R15-16 · Major · Targets: CONTRACT, KLN, AGT, PLT, UIX
**Section:** Contract 2 (Fidelity), 5 (`PriorityClass`), 12 (the `PoolLane` rename); KLN "Scheduling and cancellation"; AGT "Scheduling on Kiln workers"; PLT D-PLT-13; UIX "Interactive edit lane"
**Problem:** "Interactive" names a fidelity, a `PriorityClass`, a `PoolLane` and UIX's edit lane, and they do not line up: the `Interactive` priority class runs on the `Foreground` lane, while the `Interactive` lane serves drags. KLN's table also adds a fifth class, "`Interactive`, drag", which AGT's four-row class table lacks. Contract 12 renamed PLT's pool priority to avoid exactly this kind of clash and left the worst one in place.
**Evidence:** PLT: "`pub enum PoolLane { Interactive, Foreground, Background }`"; "AGT's interactive `PriorityClass` to `Foreground`". KLN: "`Interactive`, drag | … | `Interactive`"; "`Interactive` | A person waiting … | `Foreground`". AGT's class table has `Interactive`, `Agent`, `Ci`, `Batch`.
**Fix:** Keep `Interactive` only as a fidelity. `PoolLane` becomes `Drag`, `Foreground`, `Background`; `PriorityClass` becomes `Drag`, `Foreground`, `Agent`, `Ci`, `Batch` in AGT, KLN and `base`; UIX's "interactive edit lane" becomes "the drag lane". Add "interactive" (for lanes or classes) to the glossary's "Never call it" column.

### R15-20 · Major · Targets: KLN, CONTRACT, COV, AGT
**Section:** KLN "Items" (parts-policy package, D-KLN-47), "Revisions and lifecycle states" ("A policy package may replace the state machine"), "Change orders" (allowances); contract 7.1 Hardware CI and 7.6 (site policies)
**Problem:** "Policy" means five unrelated containers: Cedar policies, "policy packages" (parts, numbering, lifecycle, allowances), signed site policies (`unattended_safe`, `start_print`), the `PlacementPolicy` trait and "policy classes" of change orders. Policy packages change check verdicts (the parts-policy check, allowances), yet no tab says which repository holds them, how a design pins them or how they enter a key. A parts-policy update would change verdicts of unchanged Changes.
**Evidence:** KLN: "An organization parts-policy package lists approved `Purchased` Items"; "A policy allowance (contract 5) is a policy-package record changed only through `propose.policy` with two signers". No pinning rule appears in KLN, ECO or the contract.
**Fix:** A policy package is an ordinary Package in the organization's policy repository, versioned and signed like any other, pinned in each design's `ingot.lock` and updated by a bot Proposal like any dependency. Evaluation reads it only through that pin, so its records enter traces and keys. Changing the policy repository itself needs the signers of R15-15's table. Cedar policies stay separate, because they authorize `api` calls and never feed evaluation. Rename "site policy" to "site safety record" and "MCO policy class" to "MCO scope", so "policy" names only Cedar and policy packages.

### R15-23 · Minor · Targets: CONTRACT, KLN, AGT
**Section:** Contract 2 (Change); KLN "Change orders"
**Problem:** "Change" is a microversion, while "change request", "change order", "change notice" and "manufacturing change order" are PLM records over many Changes. A PLM reader reads "change order" as an order of Changes. KLN also writes "MCO" but avoids "ECO", because ECO is a tab code.
**Evidence:** Contract 2: "**Change** | One immutable fine-grained edit, like an Onshape microversion." KLN: "Engineering change order | A Proposal with lifecycle scope"; "Manufacturing change order (MCO)".
**Fix:** Keep the industry PLM terms, and add to contract 2's "Never call it" column for Change: "a change order, request or notice". Spell out "engineering change order" and "manufacturing change order" everywhere, with no abbreviations, so MCO goes and ECO never appears.

### R15-27 · Minor · Targets: CONTRACT, ING, KLN, AGT
**Section:** Contract 7.6 (error codes); ING "Diagnostics"; KLN failures
**Problem:** An agent meets three error-naming schemes: `<family>/<code>` from `api` (`label/write_down`), numeric codes from Ingot (`ING6401`), and bare Rust variants in failures (`CalibrationExpired`, `ShareQuotaExceeded`, `ResidencyDenied`, `LockHeld`). The contract says errors take the first form.
**Evidence:** Contract 7.6: "Error codes take the form `<family>/<code>`". ING: "`ING3001`"; KLN: "fail with `CalibrationExpired`".
**Fix:** One rendering everywhere: `<family>/<code>`, with ING's numbers in family `ing` (`ing/3001`, lints as `ing/l-fragile-selector`) and every typed `Failure` variant mapped to `<owner family>/<snake_case>`. AGT keeps the family registry; ING's catalog pages index by both.

### R15-30 · Minor · Targets: CONTRACT, ING, KLN, AGT, UIX
**Section:** Contract 5 (`CallSite`, `ResultStatus`)
**Problem:** `LiteralSite` crosses five tabs and enters node keys, but the contract never defines it. `ResultStatus::Proxy` appears in contract 5 and the 13.3 drag row with no definition.
**Evidence:** ING: "literal overrides keyed by `LiteralSite` (statement identity, call identity, argument slot)"; KLN rule 5 under Keys; AGT and UIX interface rows. Contract 5: "`Pending`, `Proxy`, `Ready(Fidelity)`, …".
**Fix:** Contract 5 adds "`LiteralSite` [ING]: a `CallSite` plus an argument slot; overrides key by it and follow `#[was]`" and "`Proxy`: a dependent shown by affine extrapolation from its last value while it recomputes, never cached".

### R16-01 · Critical · Targets: CONTRACT, AGT, UIX, MFG, KLN
**Section:** Contract 7.6 "Act approvals"; AGT "Approval limits" row; UIX approval page; MFG "Approval, transfer and physical safety"
**Problem:** Every denial blocks re-preparing a plan to the same recipients for 24 hours, and a session may hold at most three pending requests. The rule applies to human-prepared plans as well as agent ones. Approvers use rejection as their normal way to say "fix this": a shop lead rejects a program because of a feed in op 3, and a change board rejects a release because a drawing note is wrong. Under this rule the corrected program cannot go to that machine until tomorrow. A rejected release also blocks every release delivery to the organization's own ERP recipient for a day.
**Evidence:** Contract 7.6: "At most three pending requests per session; a denial blocks re-preparing a plan to the same recipients for 24 h and offers 'report as suspicious', which freezes the session." AGT's capability table: "Three pending; 24 h block after denial … `act/denied_cooldown`". UIX's Proposal review offers "Request changes" (10-ui line 498), but the approval page has only approve and deny. MFG step 4 sends every `Prototype` program through an approved `send_to_machine` plan, so prove-out rejections are routine.
**Fix:** Give the approval page three outcomes. **Approve.** **Return for changes:** closes the request with a reason and no cooldown. A new plan with a different digest may be prepared at once, and resubmitting the same digest is refused with `act/returned_unchanged`. **Deny as suspicious:** today's behaviour, which freezes the session and applies the 24 h block. Count the pending limit per (session, Act class, recipient) and apply it only to contexts with an agent in the delegation chain. Human sessions batch effects into one plan instead. Contract wording: "A return for changes closes the request without penalty; only a denial marked suspicious blocks re-preparing a plan to the same recipients for 24 h and freezes the session." Add AGT-O-9 cases for both outcomes.

### R16-04 · Major · Targets: CONTRACT, ELX, MFG, AGT
**Section:** Contract 7.6 "Firmware" and "Approval credentials"; ELX D-ELX-29; MFG "Printers, 3MF and print transfer" and "Approval, transfer and physical safety"
**Problem:** Each `flash_device` needs an Approval of one image digest and target, each `send_print_job` its own, and each `Prototype` program push its own, every one with AAL3 WebAuthn on the approval page. Embedded developers flash dozens of times an hour, makers iterate prints, and machinists re-send a program several times during prove-out. They will flash with their own probe tools and print from the slicer instead. The record that D-ELX-29 exists to keep is then never written. `standing_release` already solves the same problem for data transfers, but nothing covers physical effects.
**Evidence:** D-ELX-29: "Every client flashes a board only through the transfer Act `flash_device`". Contract 7.6: "Its Approval covers the image digest and the target". `standing_release` covers only "recipients, channel, schema, label ceiling and expiry".
**Fix:** Add one restricted Act, `bench_session`. It takes one AAL3 Approval over {the named person at the device, device serial (board, printer or machine), probe or gateway, payload kind, Software item or program Item lineage (one branch), maximum count, expiry of at most 8 h, hazard acknowledgements from the Network or machine package}. Transfers inside the session need no further Approval, but each keeps every check: read-back, hold in reset, no start, the gateway's offset check and the canonical hash. The session ends early on expiry, on a hazard change in the Network, or on a payload outside the lineage. Agents cannot open or extend one. The approval page lists every transfer in the session afterwards. Phase it with each underlying Act, with oracles AGT-O-new and ELX-O-FW-3 for count, lineage and expiry bounds.

### R16-06 · Major · Targets: MFG, KLN, AGT
**Section:** MFG "Approval, transfer and physical safety"; KLN "Change orders"; AGT D-AGT-20
**Problem:** The spec describes the full aerospace path (MCO, `Prototype`, first article, `Proven`, `Released`) and never states the minimum path for the commonest shop: high-mix, low-volume, where a program runs once. It is silent on three questions. Can the human who prepared a transfer plan approve it? Does a `Prototype` program need a manufacturing change order? How does a one-off job close without ever reaching `Released`? A one-person shop cannot tell from the tabs whether it can send its own program at all. KLN's rule that "an order's author cannot be its only approver" covers orders only.
**Evidence:** MFG step 3: "The program releases as an Item through KLN's manufacturing change order: `Prototype`, `Proven` … `Released`". KLN: "An order's author cannot be its only approver". D-AGT-20 rejects "approval by any authority holder" but does not address the preparer.
**Fix:** Add a "Minimum ceremony" table to MFG, with one row each for a one-person shop, a job shop and a regulated production shop. It states the following:
- A program Item is created in `Prototype` by its first transfer plan, without an order.
- A human who prepared a transfer plan may approve it under the Cedar policy `self_approve_transfer`, off by default, which the site's safety officer enables. AAL3 still applies.
- A one-off job closes in `Prototype` with a run record linking program, serials and results.
- An MCO is needed only to enter `Released`.

Add MFG-O-SAFE-7 for the self-approval policy and its audit.

### R16-12 · Major · Targets: KLN, AGT, UIX
**Section:** KLN "Revisions and lifecycle states", "Change orders"; AGT D-AGT-20; contract 7.6 "Act approvals"
**Problem:** Releases need "the required Approvals" from approvers "assigned … by Cedar policy". Nothing models how a change board works:
- which roles must sign (design, manufacturing, quality, customer);
- in what order, serial or parallel, and with what quorum;
- added roles triggered by content, such as quality when a special characteristic changes;
- delegation during absence;
- due dates and reminders.

Teamcenter and Windchill users rely on workflow templates of exactly this kind. Cedar can say who may approve; it cannot say who must, in which order.
**Evidence:** KLN line 552: "the required Approvals". Contract 7.6: approval requests are "assigned to named approvers by Cedar policy". No tab defines a route, quorum or delegation record.
**Fix:** Add an `ApprovalRoute` policy record to KLN's policy package. It holds ordered stages, each a set of roles with a quorum (`All`, `Any`, `AtLeast(n)`). It holds conditions over the `ApprovalSubject`, such as Item classes, safety characteristics or label `controls`, that add stages. Due dates send reminders and escalate to a named role, and never approve automatically. Delegation records name principal, delegate, scope and expiry. Delegation of a physical-effect or `controls` class needs D-KLN-41's two people, and nothing ever delegates to an agent. The approval page shows the route's progress. Phase 2, with change orders, and oracle KLN-O-CHG-3: routes complete only when every stage's quorum holds, and a delegated signature names both people.

### R16-16 · Major · Targets: KLN, MEC, AGT
**Section:** KLN "Items"; MEC "Standard parts and fasteners"
**Problem:** The Item record has a "classification" field but no classification scheme, attribute search or shape search. Part proliferation is one of the costs enterprise PLM is bought to cut. Engineers search by class and attributes ("M6 standoff, 20 mm, aluminium") or by shape before creating a new item number. Crucible already computes name-free `GeometryId`s and certified mass properties, so it could do this better than incumbents, but the spec never asks it to.
**Evidence:** KLN line 509 lists "classification" among Item record fields; nothing defines it. No `api` Read method searches Items by attributes or shape.
**Fix:**
- A classification schema in the policy package: classes with typed attributes, so units check.
- A Read method `read.search_items(class, where:, shape_like: Body, tol)`, ranked by name-free shape descriptors cached per `GeometryId`.
- A new-part Proposal that shows the five most similar released Items.
- An `Info` check, `duplicate_candidate`, above a similarity threshold.

Phase 3, with oracle KLN-O-PLM-13: seeded duplicates in a 10,000-Item corpus rank first.

### R17-01 · Critical · Targets: AGT, KLN, ING, PLT, CONTRACT
**Section:** AGT "Platform notes" and "Sessions, identity and delegation"; KLN "Storage, Git export and span provenance"; ING "Language service and tools"; contract 7.6 "Plans and local exports"
**Problem:** Every agent control keys on the principal, but on a desktop the human principal's credential sits in the OS keychain where any process the user runs can use it. An external host with a shell tool (the normal coding-agent setup) can run `crucible` subcommands, which map one-to-one onto API methods, as the human: merge R0 to R2 Proposals, endorse free text, export `internal` payloads as "audited local writes" and then send them out with its own network tool, and edit protected branches, all with no context label, no risk class and no delegation chain. The same agent editing `.ingot` buffers through the first-party VS Code or Zed extension produces spans recorded as "trusted when a person typed it", since LSP `didChange` cannot tell keystrokes from an AI extension's writes; a device key then vouches for those spans across archive import.
**Evidence:** AGT: "`crucible mcp` runs on stdio with the keychain credential [S6]". AGT D-AGT-1: "UI commands and CLI subcommands map one-to-one onto API methods." KLN: span integrity is "trusted when a person typed it or the compiler produced it", and imported spans keep integrity when "a device key of this organization signed the Change". ING D-ING-25 ships the language service "over stdio with first-party VS Code and Zed extensions". Nothing in AGT, KLN or PLT separates a human at the CLI from a process acting for one.
**Fix:** Add to contract 7.6: "A local credential without a fresh user-presence proof authenticates as the principal `agent:<org>/local/<device>` with `Declared` assurance, never as the human. Human-only methods (`propose.merge`, `propose.endorse_text`, `propose.policy`, `propose.declassify`, `propose.waive`, recipient and clearance changes, and every local write of a payload above `public`) need a WebAuthn user-verification assertion on the approval origin bound to the call's argument digest, valid for one call." In KLN, record spans arriving through LSP, file import or any channel other than the in-app editor's keystroke path as `data_untrusted` unless the user confirms the batch on the approval origin, and replace "a device key of this organization signed the Change" with "the server that witnessed the write signed its span-integrity record". AGT-O-8 gains a case: a host with a shell tool runs the CLI and an editor extension, and neither merge, endorsement, local export nor trusted spans result.

### R17-02 · Critical · Targets: CONTRACT, UIX, AGT, KLN, PLT, MFG
**Section:** Contract 7.6 "Approval credentials"; UIX "Approvals" (Credentials); PLT D-PLT-41; KLN "Electronic signatures"; MFG D-MFG-24
**Problem:** The whole Act model rests on which credentials may approve, yet enrolling a new approval credential needs only a signed-in app session. Sign-in accepts synced passkeys and SSO, so anyone who phishes an SSO session or steals a synced passkey enrols a security key they hold and approves exports, releases and machine transfers. The machine gateway trusts a server-signed approver directory, so the enrolled key reaches the shop floor too. "Synced passkeys never approve" is therefore one step from void.
**Evidence:** UIX: "Enrolment starts from a signed-in Crucible desktop or tablet app, which reports its form factor, or uses an allowlisted security key." The form factor is a client claim. NIST SP 800-63B-4 4.1.2.1 requires binding a new authenticator to need "authentication at either the maximum AAL currently available" or the new authenticator's AAL, whichever is lower, and that "the CSP SHALL notify the subscriber via a mechanism independent of the transaction binding the new authenticator" (https://pages.nist.gov/800-63-4/sp800-63b.html). D-KLN-41's two-person list does not include credential enrolment.
**Fix:** Contract 7.6 adds: "Enrolling an approval credential is itself approved on the approval origin: by an existing approval credential of the same person, or, for a person's first credential, by an `admin` with their own approval credential plus an identity check recorded in the record, effective after 24 h. Every enrolment notifies the person through their identity provider's out-of-band channel and the security contact. The approver directory the gateway pins lists credential public keys, and a key enrolled within 24 h never approves a physical-effect Act or an Act with `controls`." Add credential enrolment and revocation to D-KLN-41, drop "reports its form factor" from UIX (the BE flag already decides), and state that on macOS, iPadOS and Android platform passkeys are backup eligible, so those devices approve only with a roaming security key. UIX-O-APPR-1 gains: a synced-passkey session cannot enrol a credential.

### R17-03 · Critical · Targets: CONTRACT, PLT, AGT
**Section:** Contract 13.2 "Build program"; PLT D-PLT-40, D-PLT-45; AGT "Instruction authority and untrusted content"
**Problem:** Crucible is built by agents that read crate sources, papers, standards text and web pages, all attacker-reachable, and the same roles write code, oracles and supply-chain audits. D-PLT-40 makes the verifier agent the author of `safe-to-deploy` audits for every crate the engine links, though a crate's own comments and docs can instruct that agent. Until phase 2 the work runs "over Git" with none of AGT's labels, taint or risk classes, so nothing marks a builder context that read a poisoned page or crate, and nothing stops it writing to `core/`. The engine holds "every open repository, token and device key", so one injected audit or patch compromises every customer.
**Evidence:** D-PLT-40: "The verifier role writes it, or it is imported from audit sets the founder approves." Contract 13.2: "Until that machinery ships in phase 2, phases 0 and 1 run the same `WorkItem` record over Git". AGT's own premise: prompt injection is "a fundamental, unsolved weakness in all LLMs" [S28].
**Fix:** Contract 13.2 adds a rule for the build program from phase 0: "Every agent context that reads third-party source, a web page or a paper is `instruction_tainted`. Tainted contexts may write only to their own branches; their Changes to `core/`, `apps/`, `oracles/`, `deps/` or CI configuration need the founder's Approval with the taint sources listed. A cargo-vet audit written by an agent counts only as `agent-reviewed`, a criterion that implies `safe-to-run` in sandboxed CI and never `safe-to-deploy`; `safe-to-deploy` comes only from imported human audit sets or a quarantined review whose model sees the crate source alone, has no tools, and returns a typed verdict that the founder approves per crate version. Adding a dependency to the engine closure needs the founder's Approval." PLT-O-BLD gains a planted-instruction crate that must not receive `safe-to-deploy`.

### R17-04 · Major · Targets: KLN, AGT, CONTRACT
**Section:** KLN D-KLN-41 "Identity and authorization"; contract 13.2 "Roles"; AGT D-AGT-27
**Problem:** D-KLN-41 needs two distinct people for oracle and protected-path changes, recipient records, clearances, auto-merge policy and purges, but the program that builds Crucible has one human, and once its work moves onto AGT's machinery in phase 2 no oracle can change. Small customers hit the same wall: a two-person machine shop cannot add a supplier's recipient record when one partner is away, so it cannot send a quote, and a one-person consultancy cannot ever. No rule says what happens below two eligible people.
**Evidence:** Contract 13.2: "One human, the founder, directs the program". D-KLN-41 lists "oracle and protected-path changes" and "recipient records" among two-person items. AGT keeps a declined-finding note that "a solo phase 1 user can still merge", showing the solo case is real.
**Fix:** Add to D-KLN-41: "An organization with fewer than two eligible people runs single-person mode: each listed item needs the one person's AAL3 approval, takes effect after a 72-hour delay with notice to the organization's recorded out-of-band contact, and is marked `single_person` in the record. Items with `controls` are refused in this mode. For Crucible's own repository the second person for oracle changes is the verifier role's attested review plus the founder's Approval, recorded as `single_person`." Contract 13.2 cites it.

### R17-09 · Major · Targets: KLN, UIX, AGT
**Section:** KLN "Electronic signatures"; UIX "Approvals" (Isolation); AGT D-AGT-20
**Problem:** The tabs give two incompatible definitions of what an approver's authenticator signs. KLN's offline verifier expects the WebAuthn challenge to equal the signed `ObjectId`; UIX and AGT make it a hash of plan digest, request id and approver id. In KLN's form the meaning (`Reviewed`, `Approved`, `Released`) and the signer are outside the signed bytes, so a server could relabel a review signature as a release approval and it would still verify, which Part 11's 11.50 and 11.70 linkage requirements exist to prevent. A challenge equal to a content hash is also predictable rather than fresh.
**Evidence:** KLN: "the client data whose challenge is the signed `ObjectId`". UIX: "Each challenge is the hash of plan digest, request id and approver id." AGT: "Its challenge hashes plan digest, request id and approver id."
**Fix:** One definition, owned by KLN and cited by UIX and AGT: "challenge = SHA-256(domain tag ‖ server nonce of 16 random bytes ‖ signed `ObjectId` ‖ meaning ‖ signer principal ‖ request id). The signature record stores the nonce and the other fields, so an offline verifier recomputes the challenge." KLN-O-SIG-1 adds: a record whose meaning is changed after signing fails verification.

### R17-10 · Major · Targets: AGT
**Section:** AGT "Quarantined extraction and external hosts"; "Exfiltration channels"
**Problem:** The hosted crew may fetch web pages from any context, including one that holds `confidential` data and has read untrusted text. Forbidding URLs "built from context data" does not close the channel: an injected instruction can make the agent choose among attacker-supplied URLs, or fetch at all, in a pattern that encodes data, and every fetch also leaks through DNS. That breaks the Rule of Two that the tab adopts, since the context then holds untrusted input, sensitive access and outbound communication at once.
**Evidence:** AGT: "Crew web fetches return extracts, and no URL is built from context data." The exfiltration table allows the crew runtime "Egress only to the API, cleared endpoints and quarantined fetches".
**Fix:** Add to D-AGT-25: "A crew context may fetch only while its confidentiality label is `public`; once it reads anything above `public` it can no longer fetch. Fetch targets come from the role's allowlist or from the delegating human's goal text, never from tool results. Plan-Then-Execute roles fetch in the planning phase before reading the design." AGT-O-8 gains a bit-leak test through fetch selection.

### R17-11 · Major · Targets: AGT, CONTRACT
**Section:** AGT D-AGT-19, D-AGT-34 and "Taint and the Rule of Two"
**Problem:** A gateway-attested client counts as a clean context, the only kind that may auto-merge, but attestation proves only which client key called and which model answered. Nothing stops an attested host from giving its model a web-fetch tool, a mail tool or another MCP server whose output passes through the gateway inside the conversation. Such a context is no cleaner than a `Declared` one, which is the R11-12 problem moved one layer down.
**Evidence:** AGT: "An attested client is pre-registered, authenticates with `private_key_jwt` [S59] from a hardware key, and routes model traffic through the gateway, which enforces the allowlist and records the model." The Rule of Two table: "Clean (hosted crew or gateway-attested only)".
**Fix:** Give the gateway the check it is placed to make: "The gateway marks a context `instruction_tainted` when any model request contains a tool result or user turn that is not a Crucible response carrying the server's response signature or the delegating human's goal, and records the client's tool inventory from the request's tool list. A client whose tool list holds non-Crucible tools is attested but never clean." AGT-O-17 adds an attested host with a fetch tool, whose Proposals must be at least R2.

### R17-12 · Major · Targets: CONTRACT, AGT, KLN, ECO
**Section:** Contract 7.6 "Plans and local exports" and "Context labels"; AGT D-AGT-19, D-AGT-30; ECO "Scope and translation architecture" rule 3
**Problem:** Three tabs claim that every byte leaving a tenant goes through the `release_data` Act, but two large exits do not: every `api` response to an external MCP host goes to that host's model provider, and a human's local write of `internal` data goes wherever the local application sends it. Both exits check only the level and `controls`. A payload at `internal` that carries a `customer:` scope or a `DataLicence` forbidding third-party disclosure (a supplier NDA model, licensed handbook values) can therefore reach a model provider or a cloud-synced folder that `release_data` would have refused.
**Evidence:** D-AGT-30: "Every byte leaving a tenant goes through one Act family". ECO: "Every byte that leaves a tenant leaves through an Act (D-ECO-28)." Contract 7.6 exempts payloads "whose confidentiality label is `public` or `internal`, with no `controls` and no recipient record". AGT: "`Declared` endpoints never clear above `internal` or any `controls`", which says nothing of scopes or licences.
**Fix:** Replace the claim with the true list: "Tenant bytes leave through `release_data` Acts, through responses to cleared model contexts, and through audited local writes." Extend the local-write exemption and the `Declared` clearance to require empty `scopes` and only `DataLicence`s whose terms permit disclosure to processors, and make the default clearance of a newly registered `Declared` client `public` until an administrator raises it to `internal`. AGT-O-22 and AGT-O-17 add a scoped and a licensed `internal` payload.

### R17-15 · Major · Targets: CONTRACT, AGT, ELX, UIX
**Section:** Contract 7.6 "Firmware"; AGT D-AGT-31 (Firmware)
**Problem:** "Client flashing through `apps/platform` or WebUSB is the same Act", but a server Approval cannot bind what a client writes to a USB probe. WebUSB permission belongs to the web app's main origin, which R11-05 already treats as script-injectable, so injected script with a remembered device grant can flash any image with no Act at all. In the browser, the read-back check is performed by the same compromised code. The machine gateway verifies Approvals in its own core (D-MFG-24); client flashing has no equivalent.
**Evidence:** Contract 7.6: "Client flashing through `apps/platform` or WebUSB is the same Act." No tab says which component checks the Approval signature and image digest before bytes reach the probe.
**Fix:** Contract 7.6: "Client flashing runs only in code that verifies the Approval: in browsers, on the approval origin page after the ceremony, which holds the WebUSB grant and checks the image's SHA-256 against the approved plan; on desktops, in `apps/platform`'s flashing service, which verifies the Approval signature against the pinned approver directory as the machine gateway does. The main web origin never holds a WebUSB grant." AGT-O-21 adds a main-origin flashing attempt.

### R17-16 · Major · Targets: CONTRACT, KLN, AGT
**Section:** Contract 2 "Waiver"; KLN "Change orders"; D-KLN-41
**Problem:** A Waiver lets one authorized human make a failing `Error`-severity check count at a release gate, and nothing stops that person also being the Proposal's author, the delegating human of the agent that wrote it, or the release's sole approver. A waived safety check is the most consequential override in the system and gets less control than a recipient-record change. Policy allowances, which also turn non-passing checks into passing ones, need "two signers" by the contract but are missing from D-KLN-41's single list.
**Evidence:** Contract 2: a Waiver is "A signature record by an authorized human". Contract 5 says a policy allowance "changes only through a Proposal with two signers", while D-KLN-41 claims to be "one list [that] serves every tab" and lists neither.
**Fix:** Contract 2 Waiver adds: "A Waiver of an `Error`-severity check is signed by a `quality` principal outside the Proposal's authoring and delegation chain, and a release that relies on one needs an approver other than the Waiver's signer." Add both Waivers of `Error` checks and policy allowances to D-KLN-41, and test both in KLN-O-POLICY-1.

### R17-18 · Major · Targets: CONTRACT, KLN, AGT, ECO
**Section:** Contract 13.1 phase 0 gate and 7.1 Anvil (freedom to operate)
**Problem:** The freedom-to-operate search covers only chains A and B (SSI, Booleans, blends, tessellation, implicit lattices), but phase 1 also ships versioning with branches and merges explicitly modelled on Onshape's microversions, agent Proposals with snapshot-based review, and STEP and 3MF writers. Each is a field where incumbents file patents. A product launched on GP1 with chain D in it carries unsearched risk exactly where it copies an incumbent's named design.
**Evidence:** Contract 13.1: "a freedom-to-operate search of the phase 1 code paths of chains A and B". D-KLN-19: "Edits become immutable Changes, as in Onshape's microversions". Onshape describes the same model: "The new microversion stores a reference to the previous (parent) microversion and the actual definition change" (https://www.onshape.com/en/blog/under-the-hood-how-collaboration-works). Specific patents on it are [unverified].
**Fix:** Change the gate item to "a freedom-to-operate search of every phase 1 code path in chains A to D, with KLN's Changes, branches, merge and live sync, AGT's Proposal and review flow and ECO's AP242 and 3MF writers named", and add the same search at each later gate for that phase's new capabilities.

### R17-25 · Minor · Targets: CONTRACT, AGT
**Section:** Contract 7.6 "Act approvals"; AGT "Budgets, limits and admission"
**Problem:** The contract limits pending approval requests "per session", so an agent that opens ten sessions sends thirty requests to a busy approver. AGT's rate table applies the limit per principal, which is the bound that stops approval spam.
**Evidence:** Contract 7.6: "At most three pending requests per session". AGT: limits "are per principal at the gateway", with "at most 3 pending approval requests".
**Fix:** Contract 7.6: "At most three pending requests per delegating human across all sessions."

### R17-26 · Minor · Targets: UIX, AGT, PLT
**Section:** UIX "Approvals" (Isolation); D-PLT-41
**Problem:** The approval origin is `approve.<deployment>`, a subdomain of the main app's site, and relies on `SameSite=Strict` cookies. SameSite compares sites, not origins, so the main origin's script is same-site with the approval origin and can toss cookies onto it with a `Domain=` attribute. That allows session fixation on the very page R11-05 separated.
**Evidence:** UIX: "The page lives at `approve.<deployment>`" with "`SameSite=Strict` cookies and no CORS".
**Fix:** Require `__Host-`-prefixed, host-only cookies on the approval origin, reject requests that carry any non-`__Host-` cookie, and recommend a separate registrable domain for hosted deployments. The approval origin publishes no WebAuthn related-origins file. UIX-O-APPR-1 adds a tossed cookie.

### R17-27 · Minor · Targets: KLN, AGT
**Section:** KLN "Labels and export control"; AGT "Method catalog"
**Problem:** Label `scopes` carry organization-chosen names such as `customer:<name>` and `program:<name>`, and "every result carries its labels". Program code names and customer names are often confidential themselves, so an uncleared principal learns them from errors, where-used counts and labels attached to results it can partly see.
**Evidence:** Contract 5: scopes "such as `customer:<name>` or `program:<name>`". AGT: "every result carries its labels".
**Fix:** KLN: "A principal sees the name of a scope or control it satisfies; others see an opaque per-tenant id and the text `restricted`." AGT's errors follow it.

### R17-28 · Minor · Targets: AGT, ECO
**Section:** AGT "MCP profile", "Roles"
**Problem:** A skill is instructions by design. The hosted crew loads another publisher's role only after `policy:admin` approval, but nothing stops `skills/list` from serving an unapproved third-party role skill to an external host, whose model then follows it. That contradicts D-ECO-32, under which third-party package text is `ExternalText`.
**Evidence:** AGT: "trust in approved role skills binds only the hosted crew", and "The hosted crew loads another publisher's role only after `policy:admin` approves its version and digest."
**Fix:** "`skills/list` and `skills/get` serve only std roles and roles whose version and digest `policy:admin` approved for the organization, to every host."

### R17-30 · Minor · Targets: CONTRACT, UIX, AGT
**Section:** Contract 7.6 "Act approvals" (page contents)
**Problem:** The approval page shows "the session's purpose, marked as agent text". An injected agent's purpose ("routine; already cleared by the export officer") is a direct social-engineering line to the approver, the last control, and a label does not neutralize persuasive text.
**Evidence:** Contract 7.6: "the session's purpose, marked as agent text".
**Fix:** "The purpose appears collapsed below the typed content, as a handle with its integrity flags, and expands only on request; text from an `instruction_tainted` context carries a banner naming the taint sources."

### R17-34 · Minor · Targets: AGT
**Section:** AGT "Independent verifier" (D-AGT-12), "Risk classification"
**Problem:** `Attested`, `Declared` and "clean context" are used in D-AGT-12, the risk-class table and D-AGT-17 before D-AGT-34 and the Rule of Two table define them three sections later. A reader meets the key distinction of agent trust as an undefined term.
**Evidence:** D-AGT-12 uses "`Attested`" and "`Declared`"; D-AGT-34, which defines them, sits under "Quarantined extraction and external hosts".
**Fix:** Add `Assurance` (`Attested`, `Declared`) and "clean context" to the term table in "Scope and invariants", one line each, pointing to D-AGT-34.

### R17-38 · Minor · Targets: KLN, AGT, CONTRACT
**Section:** KLN "Storage, Git export and span provenance" and "Labels and export control"; AGT D-AGT-18
**Problem:** The rule that merging clears integrity on typed values but never on free text is stated in full in contract 5, contract 7.6, KLN twice and AGT twice, each in different words. A reader cannot tell whether "structure and typed values", "typed outputs" and "geometry, structure and numbers" mean the same set.
**Evidence:** Contract 5: "clears both flags on that input's structure and typed values". KLN: "endorses an Asset's geometry, structure and numbers". ECO: "endorses its typed outputs".
**Fix:** Keep the contract 5 sentence as the only statement, and replace each tab's restatement with "Merging clears integrity on typed values, never free text (contract 5)" plus that tab's example.

### R18-04 · Major · Targets: AGT, PLT, UIX, CONTRACT
**Section:** AGT "One catalog, several transports", Platform notes; PLT D-PLT-12, "The browser target"; contract 12
**Problem:** AGT says the desktop app, web app and CLI "link `core/api` in process", while PLT runs the engine as a separate process or worker that the UI reaches only through `api` messages. `core/api` holds the method implementations, so it depends on `repo`, `kiln`, Anvil and Flux. The desktop UI process and the browser's UI module would then link the whole engine, doubling the browser download against contract 13.3's 25 MiB first-visit cap, and the UI could call the engine in process, which D-PLT-12 forbids.
**Evidence:** AGT: "`core/api` has no transport code; the desktop app, web app and CLI link it in process." and "the page links `core/api` as Wasm and runs no models." D-PLT-12: "The UI talks to the engine only through `api`. The engine runs as an OS process on desktop, a worker in browsers". PLT's memory table gives the "UI module" its own 512 MiB.
**Fix:** Split the Surface row of contract 12 into `api-schema` (method catalog types, error namespace, canonical codec, client stub and transport traits; depends only on `base`) and `api` (the server: method implementations over `repo` and `kiln`). `apps/desktop`'s UI process, the browser UI module, `sdk/rust` and `apps/mcp`'s client side depend on `api-schema` only. `cargo xtask check-layers` fails any `apps/ui-toolkit`, `apps/renderer` or UI entry point that depends on `api`. AGT's sentence becomes: "the engine process, the browser engine worker and the CLI's local mode link `core/api`; UIs link `api-schema`."

### R18-10 · Major · Targets: PLT, KLN, AGT, CONTRACT
**Section:** PLT "Crates" (`cargo xtask check-layers`), "Threads and pools"; KLN "Cancellation"
**Problem:** Core crates run on `wasm32-unknown-unknown` in the browser engine worker, yet nothing keeps them off the parts of `std` and the ecosystem that fail there. `std::time::Instant::now()` panics on that target, `std::thread::spawn`, `std::fs` and `std::net` fail, and tokio supports only `sync`, `macros`, `io-util`, `rt` and `time` there, with timers only where the platform has them. KLN's checkpoint cadence is "every 10 ms of CPU time", which browsers cannot measure. The layering check bans OS binding crates but not these.
**Evidence:** web-time README: "Currently Instant::now() and SystemTime::now() will simply panic when using the wasm32-unknown-unknown target." tokio docs: "Enabling any other feature (including `full`) will cause a compilation failure." PLT's ban list: "`windows`, `objc2*`, `web-sys`, `winit`, `accesskit_*`". PLT's IO runtime: "tokio natively, the event loop in browsers".
**Fix:** PLT extends `check-layers` with a disallowed list for every crate under `core/`: `std::time::{Instant, SystemTime}`, `std::thread`, `std::fs`, `std::net`, `std::process`, `std::env`, and a direct dependency on `tokio` other than `tokio/sync`. `platform-api` adds `Monotonic` (a monotonic clock for watchdogs and cadences, never visible to evaluation) and `Spawner` (async tasks on the IO runtime), injected like `Storage`. KLN's cadence becomes "every 10 ms of monotonic time on the Op's thread". The suite's wasm32 jobs run every core crate's unit tests under `wasm-bindgen-test` in headless Chrome on each merge.

### R18-19 · Major · Targets: UIX, ECO, AGT
**Section:** UIX "Extending the interface" (`crucible:ui@0.1.0`)
**Problem:** The panel world returns a UI tree as `element`, a type that must contain child elements, but WIT forbids recursive types, so the package cannot be written as specified. The `use types.{…}` clauses also name an interface `types` that the package never declares.
**Evidence:** UIX: `render: func() -> element;   // element tree from data read through api`. The WIT specification: "Types, however, cannot be recursive" (https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md).
**Fix:** Declare `interface types` in `crucible:ui` with a flat tree: `record node { kind: node-kind, key: u64, parent: option<u32>, props: list<prop> }` and `render: func() -> list<node>`, nodes in pre-order with parents by index. Use the same arena form for `primitive-batch` if it nests. UIX-O-EXT-1 adds a published-WIT check that `wasm-tools component wit` parses the package.

### R18-26 · Minor · Targets: KLN, PLT, AGT, CONTRACT
**Section:** KLN "Cancellation" priority table; PLT `PoolLane`; contract 2 Fidelity
**Problem:** "Interactive" names three concepts: `Fidelity::Interactive`, `PoolLane::Interactive` and two rows of KLN's priority table ("`Interactive`, drag" and "`Interactive`"). Contract 12 renamed PLT's type to `PoolLane` to avoid collisions but kept the colliding variant names. `PriorityClass` itself, owned by AGT and placed in `base`, has no Rust definition anywhere.
**Evidence:** KLN table rows "`Interactive`, drag | A drag, edit stream or per-pointer tool | `Interactive`" and "`Interactive` | A person waiting … | `Foreground`". PLT: `pub enum PoolLane { Interactive, Foreground, Background }`.
**Fix:** `pub enum PoolLane { Pointer, Foreground, Background }` in PLT. AGT defines `pub enum PriorityClass { Drag, Waiting, Agent, Ci, Batch }` in `base`, and KLN's table uses these names. "Interactive" then means only the fidelity.

### R19-25 · Minor · Targets: KLN, AGT
**Section:** KLN BOM views and where-used; Change orders
**Problem:** Replacing an obsolete part in every assembly that uses it (a mass change) is a routine PLM operation, and Crucible could do it better than incumbents (where-used across repositories, then one Proposal per repository with CI on each), but no capability row defines it.
**Evidence:** KLN: where-used "drives change impact, end-of-life notices and vulnerability response"; no row replaces a usage across parents.
**Fix:** Add `propose.mass_change(from: Item, to: Item, scope)` (phase 3): where-used selects parents, an agent role prepares one Proposal per repository under one change order, interchangeability (D-KLN-25) decides revision versus new number per parent, and the order releases only when every Proposal passes.

### R21-02 · Major · Targets: ING, FLX, COV, KLN, MFG, ELX, AGT, UIX, PLT, MEC, ANV, ECO, CONTRACT
**Section:** Every design section's decisions; "Open questions"; "Contract change requests"; contract lead
**Problem:** The tabs read as the minutes of their own revision. Review finding ids appear as evidence inside running prose, decisions end in "(revised in round N)", "Rejected" clauses name "the round 2 rule", and "Open questions" sections list declined findings rather than open questions. A reader who was not in the review cannot use any of it, and the Adversarial review tab already owns this history.
**Evidence:** Counted before each tab's "Open questions": finding ids such as "(R3-37, R9-40)" appear 112 times in PLT, 62 in FLX, 56 in MFG and AGT, 48 in ELX, 45 in UIX, 43 in KLN, 34 in COV and 26 in ING (482 in all), while ANV, MEC and ECO show that a tab reads well without any. "(revised in round N)" appears 235 times across twelve tabs. Examples: D-ING-7 "*Rejected:* … `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)"; D-MEC-26 "*Why:* … the round 1 drafts claimed the formboard twice"; D-FLX-1 "*Rejected:* the round 1 seven-crate split"; MEC "It replaces `crucible:model`"; KLN "`crucible:product`, formerly `crucible:model`". ING's "Open questions" opens "This revision decides all nine round 2 questions" and then lists ten bullets of declined findings; MEC's question 2 and AGT's question 2 are titled "Findings declined…". The contract's lead is a version history.
**Fix:** One mechanical pass, then a rule. (1) Delete every finding id from text above "Open questions"; where the id stood in for a reason, write the reason ("a policy-clamped limit made two organizations cache different results for one key" stays, "(R3-12)" goes). (2) Delete every "(revised in round N)"; the Decisions log and `git log` keep revision history. (3) Delete "the round N rule", "formerly", "replaces" and similar history from decisions and names; a rejected alternative is described by what it is. (4) "Open questions" holds only unresolved questions; move every "Findings declined or applied in part" list to the Adversarial review tab under that tab's code. (5) "Contract change requests" holds only open requests or "None"; accepted ones are recorded in the contract's ruling log. (6) The contract's lead is one sentence: "Binding for every design agent and reviewer; where a tab disagrees with it, the contract wins." Add to `check.py` a rule that fails on `\bR\d{1,2}-\d{2}\b`, "revised in round" and "round \d" outside the Adversarial review and Decisions log tabs.

### R21-07 · Major · Targets: ANV, FLX, COV, KLN, MEC, AGT, MFG
**Section:** The lead of each tab (and the Overview's "Subsystems" paragraphs, which restate them)
**Problem:** Leads follow the "design in one breath" rule literally: they list mechanisms in terms the lead does not define, and none says what the engineer gains. ANV's lead uses "decisions", "rounds", "frozen tolerances", "fidelity" and "label-invariant" without definition; FLX's names "aggregated CutFEM on an immersed octree" before saying what Flux gives a user; COV's uses "model level" and "evidence level" undefined. Because the Overview copies the leads, the weakest prose in the spec appears twice.
**Evidence:** ANV: "Decisions use exact predicates on linear geometry and certified enclosures on curved geometry, in rounds against frozen tolerances, identically at every fidelity." FLX: "Solids use aggregated CutFEM on an immersed octree, slender walls and members use shells and beams, and contact uses fitted meshes." COV: "…whose models declare a model level, an evidence level and a `ValidityEnvelope` as data."
**Fix:** Adopt the three-sentence lead of R21-03 and replace these leads:
- ANV: "Anvil is Crucible's geometry kernel: one `Body` type holds exact B-rep, implicit, mesh and subdivision geometry, and mixing them never silently approximates. Where other kernels settle near-coincidences with a global tolerance and a best guess, Anvil proves each topological decision or reports that it cannot, so a model builds the same way on every machine. Every operation is versioned and returns the history that keeps face and edge names stable when dimensions change."
- FLX: "Flux is Crucible's simulation engine: physics is written as weak forms in Ingot, or called as std studies such as `static_stress`, and every result is a Field with a stated bound on its error. Where incumbents report a number and leave convergence to the analyst, Flux names each error source, its norm and how sure the bound is, so a check decides only when the bound supports it. It chooses the discretization per region (shells for thin walls, beams for struts, an immersed grid for solids), so nobody meshes by hand."
- COV: "COV decides which physics Crucible can honestly claim. Every physics model is a package that states where it is valid and how well it has been tested, every material is a versioned record with its statistical basis and licence, and every gap is a named record that points to a tool that covers it. A result outside its model's validated range is flagged or refused, never quietly trusted."
- KLN: "Kiln, `repo` and PLM keep a design's history and compute its results. Kiln re-runs only what an edit affects and shares results across designs by content; `repo` records every edit as an immutable Change on cheap branches and merges only when geometry, checks and connectivity still agree; PLM turns merged Changes into Items, revisions, BOMs and signed releases. The same signed store runs on a laptop, a team server, the cloud or an air-gapped site."
- MEC: "`std::mech` is everything a mechanical designer does in Crucible, from sketch to drawing, written as ordinary Ingot features anyone can read, fork or replace. Where incumbents add sheet metal, weldments and composites as separate workbenches, every domain here shares one constraint solver, one way of naming faces and one semantic tolerancing model, so the drawing, the stack-up and the inspection plan read the same tolerances. Every feature fails with a typed reason and a fix that compiles."
- AGT: "Agents in Crucible are colleagues on branches: they call the same `api` a person's clicks call, and hand their work over as Proposals that a human reviews like a pull request. An independent verifier attacks every Proposal before review. Safety lives in the server, not in the model: untrusted text never carries authority, and nothing leaves Crucible, from a release to a program sent to a machine, until a named human approves its exact plan."
- MFG: keep its third sentence, and replace "through one typed plan: Ingot intent, Wasm planning, Anvil geometry and Flux physics" with "as one typed plan that regenerates when the design changes".

### R21-08 · Major · Targets: CONTRACT, COV, KLN, MFG, AGT, ECO, OVERVIEW
**Section:** Contract section 2 ("Evidence record", "Evidence level"); COV "Evidence levels"
**Problem:** "Evidence" names at least six things: an Evidence record (a signed physical measurement), an evidence level (a model's credibility, E0 to E4), the evidence watermark (a log position), the `evidence_records` field of `CheckOutcome`, "simulation evidence" for manufacturing programs, and "sampled evidence" for query stability, plus "licence evidence" and "oracle evidence". The contract notices the clash ("Distinct from an Evidence record"; "'evidence' never names a bound kind") but keeps it. A reader of "E3 evidence" next to "Evidence records from the proof load" cannot tell a model property from a measurement.
**Evidence:** Phrase counts across the contract and tabs: "simulation evidence" 6, "evidence levels" 5, "licence evidence" 4, "oracle evidence" 3, "sampled evidence" 2, besides 15 uses of "Evidence record(s)". Contract 5: "`ApprovalSubject` … `evidence record ids`"; contract 7.6: "the posted program and its simulation evidence"; contract 5 (`Query`): "Stability … is sampled evidence".
**Fix:** Rename the evidence level to the **credibility level**, C0 to C4 (Declared, Verified, Benchmarked, Validated, Context-qualified), the term ASME V&V 40, which COV already cites for E4, uses for this idea. Reserve "evidence" for Evidence records and the watermark over them. Replace the other uses: "simulation results" for manufacturing programs, "sampled stability" for queries, "licence proof" for ABC per-model records, "oracle results" for CSA packages. Contract section 2 rows: "**Credibility level** · How well a physics model has been tested against reality, C0 to C4 (COV) · 'evidence level'"; add "credibility level" to the Evidence record row's "Never call it" column. This is a contract change; COV files it.

### R21-09 · Major · Targets: ING, MEC, KLN, ANV, AGT
**Section:** D-ING-26 and D-MEC-33; D-ING-11 and D-KLN-6; D-ING-22 and D-MEC-10; D-ANV-18, D-KLN-2 and D-KLN-4; D-AGT-31
**Problem:** Several facts are decided twice, in two tabs, with two rationales, against "Say it once". A reader meets the same rule again and has to check whether the two copies differ, and the copies already drift in detail.
**Evidence:** Sketch seeds: D-ING-26 ("Sketch seeds are inline literals rounded to a quantum") and D-MEC-33 ("Seeds stay inline, rounded to a quantum q"), each with its own rejected list. Failures and Aborts: D-ING-11 and D-KLN-6 both justify themselves with the out-of-memory fallback example. Instance existence: D-ING-22 and D-MEC-10 both decide that existence depends only on `#[configuration]` parameters. Version freezing: contract 4, D-ANV-18, D-KLN-2 and D-KLN-4, with near-identical paragraphs in ANV ("Per-merge CI reproduces golden hashes of `Current` and `Deprecated` versions pinned by a golden product or registry package … weekly in shards") and KLN ("Per-merge CI reproduces golden hashes only for `Current` and `Deprecated` versions that a golden product or registry package pins … weekly in shards"). D-AGT-31 opens "Physical-effect Acts follow contract section 7.6", restating a contract rule as a decision.
**Fix:** Keep one decision per fact, in the owner's tab: seeds in MEC (D-MEC-33); Failure and Abort semantics in KLN (D-KLN-6), with ING keeping only the language rule that `try` cannot observe an Abort; existence in ING (D-ING-22); version freezing in ANV for operations, KLN for registration. In the other tab, replace the decision with one sentence and a link ("Sketch seeds are inline literals rounded to MEC's quantum; see MEC 'Determinism and seeds'"). Decision numbers stay reserved, so mark the removed ones in the Decisions log as "merged into D-MEC-33". D-AGT-31 keeps only what AGT adds (plan schemas and AGT-O-21).

### R21-10 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT
**Section:** Running prose and table cells in every tab
**Problem:** Cross-references use decision numbers as nouns: "MEC's Part-level `part.general_tolerance(spec)` record (D-MEC-35)", "the default distribution (D-MEC-28)", "standing releases (D-AGT-33)". A reader cannot tell what D-KLN-41 is without leaving the page, and a sentence carrying three such ids reads as a lookup table. Decision numbers are stable ids for logs and reviews, not prose.
**Evidence:** Decision ids before "Open questions", per tab: AGT 101, MFG 95, ECO 90, FLX 87, KLN 86, PLT 83, ELX 77, COV 76, MEC 75, ANV 58, UIX 58, ING 51, about 940 in all. Example from AGT: "`api` enforces KLN's one two-person list (D-KLN-41), which includes this tab's items"; from KLN's interface row: "`release_data` and standing releases (D-AGT-30, D-AGT-33)".
**Fix:** Refer to facts by name and link the owning section: "KLN's two-person list ([KLN, Change control](05-kiln-repo-plm.md#change-control-signatures-and-compliance))". Keep a decision id only where the decision itself is the subject ("D-MEC-33 is merged into …") and in the Decisions log. Add a `check.py` warning for more than one decision id in a sentence outside decision blocks.

### R21-11 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** "Interfaces with other subsystems" in every tab; contract section 11, item 5
**Problem:** The Interfaces sections use at least six formats, and every interface is written four times (A provides it to B, A requires it from B, and both again from B's side), which is why the plan needs `extract.py` to reconcile rows. A reader comparing two tabs finds the same edge described in different words and cannot tell which wording is binding.
**Evidence:** Formats: ING, FLX, COV, AGT and UIX use "provides" (To · Provides · Types) plus "requires" (From · Requirement); ANV uses "Anvil provides" with columns To · What · Types; MEC one table Subsystem · MEC consumes · MEC provides; ECO Tab · ECO requires · ECO provides; MFG "What MFG consumes" with From · Canonical name or type · Used for; PLT "Provided by PLT" and "Consumed by PLT". The repository's working notes list "make each row of 'Interfaces with other subsystems' match the other tab's row" as a standing consistency task.
**Fix:** Each tab writes only what it provides, in one format: `| To | What | Types | Phase |`. `extract.py` generates the "requires" view per tab and one interface matrix (twelve by twelve, linking cells to rows) for the Overview. Change contract 11 item 5 to: "`## Interfaces with other subsystems`: one table of what this tab provides (To · What · Types · Phase); what it requires is generated from the other tabs." A requirement nobody provides then shows up as an empty cell instead of a mismatch hunt.

### R21-12 · Major · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Inline citations and "Sources" in every tab
**Problem:** The tabs use four inline citation systems, so a reader re-learns how to follow a reference in each tab, and in two of them the markers crowd the prose. COV and AGT tag almost every sentence with `[Sn]`, ELX with `[n]`, ANV and MFG use readable keys, and ING, KLN, UIX and PLT name sources in prose with no marker at all.
**Evidence:** `[Sn]` markers: COV 384, AGT 239; bare numeric `[n]`: ELX 177; bracketed keys such as `[Parasolid convergent modeling]` and `[Gardeyn et al. 2025]` in ANV, MEC and MFG; none in ING, KLN, UIX and PLT. One AGT table row carries `[S2][S4][S8]`. ELX's Sources opens "[65] to [69] were opened in round 2".
**Fix:** One style in contract section 11: readable keys `[Author Year]` or `[Organization short title]`, defined in Sources as "key · title · URL · date opened", and at most one marker per sentence. Convert COV, AGT and ELX mechanically from their source lists; add markers in ING, KLN, UIX and PLT where a sentence states a sourced fact. Remove round history from Sources headers.

### R21-13 · Major · Targets: PLT, FLX, MFG, AGT
**Section:** PLT "Targets" and "The browser target"; body prose of the tabs with finding ids
**Problem:** Some quotations from primary sources are attributed to review finding ids instead of the page that was opened, so the reader cannot follow the citation and the research rule ("cite only pages you opened") is met only in the Sources list. The finding id is not a source; it is the reason the sentence was added.
**Evidence:** PLT: "Wasmtime rates Windows ARM64 Tier 3, lacking 'CI testing, full-time maintainer', and aarch64 macOS and Linux Tier 2, lacking 'Continuous fuzzing' (R6-12)." PLT D-PLT-33: "Pulley carries 'a ~10x order-of-magnitude slowdown' (R6-13)". PLT's Sources do list the pages ("67. Wasmtime stability tiers. https://docs.wasmtime.dev/stability-tiers.html"; "68. Pulley, Wasmtime documentation"), but the prose never points to them.
**Fix:** Replace each finding id that follows a quotation or a sourced fact with the source key (R21-12): "(R6-12)" becomes "[Wasmtime stability tiers]", "(R6-13)" becomes "[Wasmtime Pulley]". Do this as part of R21-02's pass: where an id follows a quote, swap it for the source; elsewhere, delete it.

### R21-14 · Major · Targets: OVERVIEW, ING, ANV, FLX, COV, MEC, AGT, CONTRACT
**Section:** Overview "Program plan", "Phase 1 scope", "Roadmap"; tab-local terms throughout
**Problem:** Terms and abbreviations appear before any definition, and some are never defined in the tab that uses them. The Overview, the page meant for every reader, uses DWR, SSI, CutFEM, PMI, WIT, MCP and DAE without expanding them, and refers to "chains A and B" and "GP2's alloy, machine, bureau and build-preparation software" in the Roadmap table, sixty lines before "Critical path" defines the chains. The contract glossary covers platform concepts but not the technical vocabulary the tabs share.
**Evidence:** First Overview uses: "WIT package" (line 51), "compiled into a DAE" (77), "aggregated CutFEM" (145), "chains A and B searched" (282), "semantic PMI" (283), "Aggregated CutFEM with calibrated DWR" (333), "Certified SSI without sampling for GP1 and the prismatic ABC subset" (334); none is expanded. η99 is used in COV and MEC and defined only in FLX D-FLX-24; ρ appears in MEC's D-MEC-33 ("2¹⁰ρ") with no definition in MEC; "torsor", "Krawczyk test", "pass^4", "MRTR" and "Rule of Two" appear without a gloss at first use.
**Fix:** Add a generated "Glossary" at the end of the Overview, listing each term once with a one-line meaning and its owner, and require first-use expansion in every tab (contract 11). Entries to add:

| Term | Meaning | Owner |
| --- | --- | --- |
| SSI | Surface–surface intersection: computing the curves where two surfaces meet, the core of every Boolean | ANV |
| CutFEM (aggregated) | Finite elements on a background grid that the geometry cuts through, so no fitted mesh is needed; "aggregated" merges tiny cut cells with neighbours for stability | FLX |
| DWR | Dual-weighted residual: an error estimate for one goal quantity, such as a regional stress average, computed with an adjoint solve | FLX |
| η99 | A calibration class's 99th-percentile underestimate factor; every `Estimated` bound is reported already multiplied by it | FLX |
| ρ | A Body's resolution: the scale-relative length below which Anvil treats geometry as coincident | ANV |
| PMI | Product and manufacturing information: dimensions, tolerances and notes attached to the 3D model; "semantic" PMI is machine-readable | MEC |
| Torsor | The small rigid displacement (three rotations, three translations) by which a toleranced feature may deviate from nominal | MEC |
| Krawczyk test | An interval-arithmetic test that proves a system of equations has exactly one solution in a box | ANV, MEC |
| DAE | Differential-algebraic equations, the form a Network compiles to | FLX |
| WIT | WebAssembly Interface Types, the interface language of the Wasm Component Model | ECO |
| MCP | Model Context Protocol, the standard through which AI hosts call tools | AGT |
| IIR; kernel IR | The Ingot IR, Ingot's dataflow form after lowering; FLX's intermediate form for every result-affecting numeric kernel | ING; FLX |
| Golden product (GP1 to GP16) | A reference product whose checks, and whose made and measured articles, close a phase | Contract 13.1 |
| Chains A to D | The four sequences of work on phase 1's critical path: geometry, physics, interface, release | Contract 13.2 |
| ABC subset | The licence-filtered part of the ABC dataset of public Onshape models used for benchmarks | Contract 13.3, ECO |
| R0 to R4 | Risk classes of a Proposal, from no semantic change to changes that feed an Act | AGT |
| pass^k | The share of tasks an agent completes in every one of k independent trials | AGT |
| UFL | Unified Form Language, FEniCS's notation for weak forms, whose semantics Flux's forms follow | FLX |

In the Overview, move the Roadmap's phase 0 gate details on chains and GP2 behind a link to "Critical path", or define the chains before the table.

### R21-17 · Major · Targets: AGT
**Section:** "The `api` surface", "MCP profile"
**Problem:** The tab's first design section after scope is protocol detail: MCP revision deprecations, Multi Round-Trip Requests, HTTP header mirroring, HMAC-truncated shard keys, AEAD-sealed request state and a tool-name character rule. A reader has not yet seen an agent do anything, so none of it has a reason. The tab's strongest material (an agent editing, checking, describing and proposing work on the bracket) is spread over four later sections.
**Evidence:** The first subsection under "The `api` surface" is "MCP profile", whose second paragraph reads: "Mirrored headers are visible to intermediaries [S3], so `shard_key` is an HMAC-SHA-256 of the repository id under the tenant's routing key, truncated to 16 bytes." The bracket's `inspect.describe` output, the best example in the tab, sits in "Observation interfaces", about 350 lines later.
**Fix:** Open AGT's first design section with "An agent's task, step by step", a numbered trace on the bracket: `session.open` as a detail designer on branch `widen-bracket`; `read.outline` of `bracket`; `edit.apply` with `SetParameter { width: 80mm }` returning the source patch; `evaluate.ci` streaming frames; `inspect.describe` returning the brief description already in the tab; `propose.create` with its five preconditions; the verifier's attack; risk class R1; a human approves the merge. Each step links to the subsection that specifies it. Move "MCP profile", HTTP headers and `shard_key` into a "Transports" subsection near the end of "The `api` surface", or into the Reference section (R21-03).

### R21-21 · Minor · Targets: CONTRACT, AGT, COV, KLN, MEC, MFG
**Section:** Contract section 2; uses of "class"
**Problem:** "Class" carries eleven meanings: platform, calibration, risk, Act, machine, execution (EN 1090), device, response-quantity, precision, retention and priority class. Several meet in one sentence ("a non-provisional `Pass` in a platform class the gate accepts … calibration class … risk class"), and "the canonical class" appears bare.
**Evidence:** Occurrences: risk class 15, calibration class 14, platform class 13, Act class 12, machine class 10, execution class 8, device class 8, response-quantity class 7, precision class 6, retention class 3, priority class 3.
**Fix:** Keep platform, calibration, risk, machine and execution class (core terms or industry usage). Rename Act class to **Act kind**, precision class to **precision tier**, retention class to **retention tier**, and say "response quantity" (the V&V term) instead of "response-quantity class" where the set is meant. In each tab, write "the canonical platform class" at first use.

### R21-22 · Minor · Targets: CONTRACT, ING, MEC, AGT
**Section:** Contract sections 9 and 11, "Platform notes"
**Problem:** Every tab must have a "Platform notes" section, so tabs with no platform-specific behaviour fill it with restatements, which a reader skims and learns to ignore.
**Evidence:** ING: "Accessibility | Diagnostics are plain text with spans"; "Air-gapped installs | Compiler and interpreter ship in every build; no network is needed"; "Every target | One canonical-class interpreter, so a divergence is a platform defect".
**Fix:** In contract 9 and 11, allow "Platform notes: none beyond PLT's rules" as a complete section, and require a row only for behaviour that differs by target (capacity, a missing capability in a tier, a browser limit).

### R21-23 · Minor · Targets: KLN, AGT
**Section:** AGT before "Method catalog", "Roles", "Proposals and review", "Clearance, egress and data protection", "Benchmarking and training data"; five places in KLN
**Problem:** A `##` heading follows a table row with no blank line. GitHub renders it, but a stricter Markdown renderer or the publishing step can fold the heading into the table, and the source reads as one block.
**Evidence:** AGT lines 275, 454, 623, 827 and 998 are `## …` headings directly after a capability-table row; KLN has five such headings.
**Fix:** Insert the blank lines, and make `check.py` fail on a heading directly after a table row.

### R21-24 · Minor · Targets: ING, AGT, FLX, MEC, ANV, KLN
**Section:** "Oracles"
**Problem:** Oracle ids follow different schemes: flat numbers (ING-O-1 to ING-O-38, AGT-O-1 to AGT-O-24) and area-prefixed ids (MEC-O-PF-1, ANV-O-VER-1, KLN-O-FPRINT-1, FLX-O-OPT-1). A flat id says nothing about what it verifies, so a capability row citing "ING-O-8" or "AGT-O-17" sends the reader to the Oracles table every time.
**Evidence:** ING capability rows cite "ING-O-1, ING-O-13, ING-O-27"; MEC rows cite "MEC-O-TL-6", whose area (tolerancing) is readable in place.
**Fix:** Adopt `<TAB>-O-<AREA>-<n>` in ING and AGT now, while `oracles/` holds no executable oracles and renaming costs one search-and-replace across tabs.

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

### R21-31 · Minor · Targets: AGT
**Section:** "Budgets, limits and admission"; "Scheduling on Kiln workers"
**Problem:** Some sourced figures lack the referent that makes them meaningful.
**Evidence:** "Concise detail, the default, uses about a third of the tokens [S31]" (a third of what?); "Anthropic's Opus 4 lead with Sonnet 4 subagents beat one Opus 4 agent by 90.2% [S33], which golden tasks test" (on what measure, and what do golden tasks test?).
**Fix:** "Responses default to concise detail; a concise response uses about a third of the tokens of a detailed one [S31]." "On Anthropic's internal research evaluation, an Opus 4 lead with Sonnet 4 subagents outperformed a single Opus 4 agent by 90.2% [S33]; golden tasks measure whether the same split helps design work."

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

None in this review.

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-3`.

None.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

1. **R1 thresholds.** Are a 90% margin floor, 0.5 mm deviation and 1% cost increase right? They stay defaults until auto-merge ships in phase 2, whose review data can set them.
2. **Findings declined in part.**
    - R11-12: an unattested verifier review shows as `Declared` and needs a human approval beside it. It still counts, so a solo phase 1 user can merge.
    - R12-02: the work item maps onto `WorkItem`, but plans ship in phase 2, so contract 13.2 runs the `WorkItem` record over Git until then (CCR-AGT-13).
    - R11-19: standing-release transfers are effects of one approved plan; contract section 7.6 says so (CCR-AGT-10).
    - From round 2: R3-53 (title fixed); R4-01 (physical Acts in phase 2); R5-18 (contract names stand). R4-05 (MFG owns headers, offsets and drip feed); R6-02 item 6 (three phase 1 roles).

## Known items

- Read `docs/revision/digest.md`: adopt the permissive libraries that serve your tab, name copyleft tools only as oracles, and use the clean-room insight protocol of contract 7.7 for incumbent behaviour.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/09-agents-swarm-flow.jsx`, `diagrams/09-agents-act-sequence.jsx`).
