# ECO round 4 packet

Your tab is `docs/spec/11-interop-ecosystem.md` at v3 (tag `round-3`). Round 4 fixes, in one pass: the 40 third-review findings that target it (0 Critical, 28 Major, 12 Minor), its 0 `[unverified]` claims, its open questions and the known items below. Contract v7 is binding; its section 18 lists the rulings on this review, and many findings below are already settled there.

## Third-review findings

### R14-06 · Major · Targets: ANV, MEC, ECO
**Section:** ANV Per-entity tolerances (λ), Cellular topology (`anvil::exchange_form`); MEC Model-based definition, `check::standards`
**Problem:** Anvil's minimum size λ = 2⁴ρ is about 1.9 nm on the GP1 bracket, below Parasolid's 5 nm default tolerance and far below the micrometre tolerances many receivers use, so Anvil can legally export edges and sliver faces that the shop's CAM or CMM software treats as degenerate. Tolerant edges from healing or contact curves can also exceed a receiver's tolerance and arrive as gaps. `exchange_form` adds seams and approximates procedural faces "within a stored bound", but no profile states the receiver's tolerance or minimum feature, and the bound is not tied to the tolerances on the face, although a profile tolerance on a fillet is then checked against the approximation.
**Evidence:** ANV: "Minimum size λ: 2⁴ρ"; GP1's ρ ≈ 0.12 nm. Jackson 1995 gives Parasolid's default tolerance as "normally 5.0e-9 metres" (https://ftp1.cs.wisc.edu/pub/users/prem/jackson-SM-95.pdf). Contract 13.1: GP1 is "made by a reference shop from Crucible's STEP AP242 ... using the shop's own CAM".
**Fix:** Give `exchange_form`'s receiver profile `tolerance` and `min_feature` fields, with named profiles (Parasolid-based receivers at 5 × 10⁻⁹ m by default, others declared by the organization). `exchange_form` merges entities below `min_feature` within tolerance or fails with `NotRepresentable { entities, reason: BelowReceiverResolution }`, and reports every edge whose τ exceeds the profile's tolerance. Set the default approximation bound for each procedural face to min(1% of the tightest tolerance whose target includes the face, the profile tolerance). Add `export_resolution` to MEC's `check::standards`, run before any export Act, and an oracle that exports a part with a 3 nm sliver and a 10 µm tolerant edge under the Parasolid profile and expects both reported.

### R14-15 · Major · Targets: ANV, ECO, MEC
**Section:** ANV Imported and non-B-rep entities (D-ANV-31), capability `anvil::match_bodies` (phase 2)
**Problem:** Without persistent ids, an imported face is named by "a hash of its exact parameters and an adjacency signature". A supplier's revised STEP file changes the parameters of every face the revision moved and of any face whose numbers the exporter rewrote, so every mate, PMI target and drawing item on those faces fails with a `ResolveError`. Updating a supplier's part is routine work, and `match_bodies`, the only remedy, arrives in phase 2, after the phase 1 enclosure checks against imported boards.
**Evidence:** ANV: "Otherwise it is the surface type with a hash of its exact parameters and an adjacency signature"; `anvil::match_bodies` phase 2. MEC: `check::enclosure` "reads STEP board assemblies in phase 1".
**Fix:** Move a minimal `match_bodies` to phase 1: on re-import of an Asset at the same import site, match faces of equal surface type whose parameters agree within the import's healing tolerance and whose adjacency graphs agree, and write the result as an `import_map` Proposal with a geometry overlay. Faces the match cannot pair keep failing with `ResolveError`, and the reviewer sees exactly which. Add an ANV-O-NAME-4 case: a board re-exported with one connector moved keeps every other reference.

### R15-32 · Minor · Targets: KLN, PLT, ECO, CONTRACT
**Section:** Interfaces with other subsystems (KLN, PLT, ECO); contract 12 (`apps/attestation`)
**Problem:** Three facts have two owners. KLN requires "the egress proxy" from ECO, while contract 7.8 and KLN say PLT enforces egress and PLT provides it. KLN requires "attestation" from PLT, while contract 7.8 and KLN's role table make the attestation service KLN's, and contract 12 lists `apps/attestation` without an owner. KLN owns `crucible:host`, while PLT provides `crucible:host/parallel`.
**Evidence:** KLN requires: "ECO | … the egress proxy"; "PLT | … attestation; egress". PLT provides KLN "attestation … label-aware egress". ECO requires from PLT "`crucible:host/parallel`".
**Fix:** Egress: PLT. Attestation service and `apps/attestation`: KLN, packaged by PLT. `crucible:host`: KLN owns the WIT package, and PLT implements `parallel` behind it. Fix the three interface rows and name the owner in contract 12.

### R16-08 · Major · Targets: MFG, ECO
**Section:** MFG "Machines, controllers and posts"
**Problem:** Simulation, posts, the gateway and program classes all depend on a machine package: kinematic chain, envelope, limits, spindle curves, tool changer and `MotionSemantics`. The tab says only "Builders publish machine packages, shops extend them". It has no capability row, contract, failure or oracle for building one. Machine builders rarely publish open kinematic models; shops get them from their CAM or verification vendor. GP3 in phase 2 needs the reference shop's machines modelled before any program can pass simulation.
**Evidence:** No capability table in MFG names machine-package creation. "Forward and inverse kinematics" assumes a `Machine` exists. MFG-O-POST-3 qualifies a post, not the kinematic model behind it.
**Fix:** Add the row "Machine package builder", phase 2. Its contract: `machine(structure: Asset, axes: [Axis { joint: Query, travel, rapid, accel, jerk }], spindles, tool_changer, controller) -> Machine`, built from the builder's STEP and spec sheet. Its failures are typed checks: the chain closes, travels match the spec, the home pose is collision-free, and pivot and offset lengths agree with the control's kinematic parameters read through a connector. Add oracle MFG-O-KIN-3: the reference shop's machines, built from STEP and spec sheets, reproduce the controls' stored kinematic parameters within 0.01 mm and the captured crash corpus. ECO lists any machine-definition formats Crucible reads, each with its licence check.

### R16-11 · Major · Targets: MEC, ECO
**Section:** MEC D-MEC-31; "Holes and threads"; "Standard parts and fasteners"; Open question 1
**Problem:** Thread diameter–pitch series, clearance holes and fastener dimensions are licensed data packages awaiting counsel, and "until then an organization supplies its own table packages". `ThreadSpec::iso_metric("M5")`, the tab's own example, needs ISO 261's coarse pitch, so a new user's first tapped hole can fail `UnknownSize`. Standard fasteners arrive only in phase 2, and only as licensed packages. Engineers used to free toolbox libraries and supplier catalogues would meet a paywall or an error on their first day.
**Evidence:** D-MEC-31; MEC's "Holes and threads" table marks `crucible::standards::thread_plans` and `clearance_holes` as "Licensed data"; Open question 1. The formula packages (`iso_metric_thread`, `unified_thread`) already compute profile and tolerance once diameter and pitch are given.
**Fix:**
1. Designations that carry their pitch (`M5x0.8`, `1/4-20 UNC`) resolve from the formula packages with no table. The UI always writes the explicit form, so source never depends on a series table.
2. The coarse-pitch lookup stays a data package, decided with counsel.
3. Clearance holes default to a Crucible-defined rule (nominal plus a class allowance), labelled `CrucibleDefined` and checked, until ISO 273 data can ship.
4. Fastener geometry defaults to manufacturers' `parts::` packages published under their own terms (D-ECO-18), the model supplier catalogues use. Standard-dimension packages stay optional.

State in the phase 1 row that a design compiles with no licensed package installed.

### R16-13 · Major · Targets: ELX, KLN, ECO
**Section:** ELX D-ELX-5, "Catalog parts"; KLN "BOM views and where-used"; ECO D-ECO-18
**Problem:** Offers and catalog definitions change only through an explicit update, and part lifecycle sits in a pinned facet. Nothing tells a released product that one of its parts has gone end-of-life or received a product change notice. Electronics and parts engineers track obsolescence weekly; it is the main reason released BOMs change. KLN's where-used index "drives … end-of-life notices", but no tab produces the event, owns the check or defines the report.
**Evidence:** D-ELX-5: "changed by an explicit update". KLN line 572 names end-of-life notices as a use of where-used. No capability row anywhere covers lifecycle monitoring. A search of the spec for "obsolescence" and "PCN" finds only the `Obsolete` state.
**Fix:** ECO's catalog connector emits `part.lifecycle_changed` and `part.change_notice` events, applied as dated External input updates on a monitoring branch, never on released source. KLN adds a nightly check, `obsolescence`, over the where-used of released revisions. For each end item it reports the affected Items, effectivity, alternates found by re-running each `CatalogSelection` with the part excluded, and a last-time-buy quantity from MBOM demand when ERP supplies it as an External input. Each finding opens a change request. Phase 3, with oracle KLN-O-PLM-12.

### R16-18 · Major · Targets: MFG, KLN, ECO
**Section:** MFG "Factory connection and digital twin" (MBOM and routings); KLN "BOM views and where-used"
**Problem:** The MBOM is one view derived from EBOM rules, with routings and work centres. Real products are often made in two plants, or by a contract manufacturer and an in-house line, each with its own MBOM, routings, programs and suppliers for the same EBOM revision. Nothing keys an MBOM or routing by site, so MBOM reconciliation, cost and ERP mapping assume a single factory.
**Evidence:** MFG's MBOM row: "EBOM-to-MBOM rules as Ingot (phantoms, kits, stations, consumables); routing steps with times and work centers". KLN: "MBOM | Phantoms, kits, raw stock, consumables, manufacturing-only Items". No "plant" or "site" appears in either tab.
**Fix:** Key MBOM, routings and work centres by (EBOM configuration point, `Site`). `Site` is a policy record naming the plant or supplier and its ERP mapping. Run MBOM reconciliation per site, compute cost per site, and let the ERP connector map per plant. Program Items already bind machine classes, so they need no change. Phase 3, with oracle MFG-O-FAC-8: two sites with different routings both reconcile against one EBOM.

### R17-05 · Major · Targets: ECO, PLT, CONTRACT
**Section:** ECO "Publishing and signing" (steps 2 to 7), D-ECO-8; PLT "The determinizer"; contract 7.4
**Problem:** For third-party packages the determinizer runs on untrusted-evaluation workers, the same pool that runs the package's test vectors, and hosts then "execute only determinized binaries" without checking that the bytes carry the fuel, stack and NaN instrumentation. A package that escapes during its own tests can substitute an uninstrumented binary whose hash the registry signs. Fuel metering and cancellation are then gone on every host, and NaN payloads become observable. The determinizer is deterministic, so the check is cheap, but no tab requires it.
**Evidence:** ECO: "For a third-party package, steps 2, 3, 5, 6 and 7 run on untrusted-evaluation workers". PLT: "Hosts execute only determinized binaries, whose hash enters the `OpKey`"; load-time verification is specified only for Ingot code-generator output ("Ingot code generator output is verified, not rewritten").
**Fix:** In ECO's pipeline, run step 3 in a separate single-use microVM that runs no package code, with the host computing the output hash, and repeat it on a second host; the index entry records both receipts. In contract 7.4 and PLT add: "Every host, at install, re-runs `determinize@N` on the published input binary and refuses the component when the output hash differs from the index entry", with PLT-O-WASM-1 covering a substituted uninstrumented binary.

### R17-06 · Major · Targets: ECO, PLT
**Section:** ECO "Names and namespaces" (New versions); PLT D-PLT-40
**Problem:** Both holds on new versions (72 hours in the registry, 14 days for Crucible's own dependencies) are skipped for any version that "fixes" an advisory. The worm case the holds exist for, a hijacked maintainer account as in Shai-Hulud, can publish an advisory and a "fix" together, so the malicious version resolves at once. Neither tab says who may file the advisory or how a fix is verified.
**Evidence:** ECO: "except one that fixes a published OSV advisory, which resolves at once with a flag". D-PLT-40: "a new version waits 14 days unless it fixes an advisory". D-ECO-15 cites the Shai-Hulud worm as the threat.
**Fix:** Replace both exceptions with: "A version skips the hold only when the advisory was published by a party other than the package's publishers (the registry security team, OSV's upstream database or a CNA), the fixing version comes through the namespace's trusted publisher with an unchanged signer, and its diff from the previous version is limited to the advisory's affected files or is reviewed by the registry security team." ECO-O-19 adds a self-filed-advisory case.

### R17-07 · Major · Targets: ECO, KLN
**Section:** ECO D-ECO-29 "Security, sanctions and notices"; KLN "Modes"
**Problem:** Round 3 replaced the round 2 rule ("comprehensively sanctioned jurisdictions") with a Russia and Belarus rule and lists the old rule as rejected, so the hosted service, updates, marketplace and support no longer refuse Cuba, Iran, North Korea, Syria or the occupied regions of Ukraine. Those embargoes remain in the EAR, and hosted services there also fall under OFAC programs. The tab now says less than before.
**Evidence:** D-ECO-29: "A sector rule refuses tenants, buyers, support customers and update clients located or established in Russia or Belarus"; *Rejected:* "Restricting only comprehensively sanctioned countries (round 2)." 15 CFR part 746 keeps sections for Cuba (746.2), North Korea (746.4), the Crimea and covered regions of Ukraine (746.6), Iran (746.7) and Syria (746.9) beside Russia and Belarus (746.8) (https://www.law.cornell.edu/cfr/text/15/part-746).
**Fix:** Rewrite the rule: "Onboarding, purchases, support and update clients are refused for parties located or established in a jurisdiction listed in the pinned restricted-jurisdiction dataset, which holds every country or region under a comprehensive EAR part 746 or OFAC embargo plus the EU and US sector restrictions on Russia and Belarus. Counsel signs each dataset version." Keep "comprehensive embargoes" in the decision and move only "restricting only" to *Rejected*.

### R17-08 · Major · Targets: ECO, PLT
**Section:** ECO D-ECO-10 "Isolation and platforms"; PLT D-PLT-43 and PLT-O-WASM-6
**Problem:** The browser sandbox for third-party Wasm components relies on `default-src 'none'` to stop exfiltration, but CSP's fetch directives do not govern WebRTC. A component that escapes the Wasm sandbox into the iframe's script can open an `RTCPeerConnection` and leak its labelled inputs through ICE candidates to an attacker's STUN or TURN server. The oracle tests `fetch`, WebSocket, script import and navigation only, so it would pass this.
**Evidence:** CSP Level 3 puts `webrtc` among "Other Directives", separate from the fetch directives that fall back to `default-src`, and describes it as the directive that "restricts whether connections may be established via WebRTC" (https://www.w3.org/TR/CSP3/). PLT-O-WASM-6: "a browser sandbox worker cannot `fetch`, open a WebSocket, import scripts or navigate".
**Fix:** Run the component in a dedicated worker started by the sandbox iframe, since workers expose no `RTCPeerConnection` [unverified per engine], and add `webrtc 'block'` to the iframe's policy where engines implement it. Add to PLT-O-WASM-6: "no `RTCPeerConnection`, DNS prefetch or `<link rel=preconnect>` leaves the sandbox", tested in every Tier 1 browser engine; until it passes there, that engine evaluates third-party components remotely.

### R17-12 · Major · Targets: CONTRACT, AGT, KLN, ECO
**Section:** Contract 7.6 "Plans and local exports" and "Context labels"; AGT D-AGT-19, D-AGT-30; ECO "Scope and translation architecture" rule 3
**Problem:** Three tabs claim that every byte leaving a tenant goes through the `release_data` Act, but two large exits do not: every `api` response to an external MCP host goes to that host's model provider, and a human's local write of `internal` data goes wherever the local application sends it. Both exits check only the level and `controls`. A payload at `internal` that carries a `customer:` scope or a `DataLicence` forbidding third-party disclosure (a supplier NDA model, licensed handbook values) can therefore reach a model provider or a cloud-synced folder that `release_data` would have refused.
**Evidence:** D-AGT-30: "Every byte leaving a tenant goes through one Act family". ECO: "Every byte that leaves a tenant leaves through an Act (D-ECO-28)." Contract 7.6 exempts payloads "whose confidentiality label is `public` or `internal`, with no `controls` and no recipient record". AGT: "`Declared` endpoints never clear above `internal` or any `controls`", which says nothing of scopes or licences.
**Fix:** Replace the claim with the true list: "Tenant bytes leave through `release_data` Acts, through responses to cleared model contexts, and through audited local writes." Extend the local-write exemption and the `Declared` clearance to require empty `scopes` and only `DataLicence`s whose terms permit disclosure to processors, and make the default clearance of a newly registered `Declared` client `public` until an administrator raises it to `internal`. AGT-O-22 and AGT-O-17 add a scoped and a licensed `internal` payload.

### R17-17 · Major · Targets: ECO, CONTRACT
**Section:** ECO D-ECO-21 "Licence and contributions", D-ECO-20, D-ECO-22; contract 7.7 "Licensing", 13.2
**Problem:** Crucible's code is written by agents, and the only human, the founder, is supposed to add a DCO sign-off that "certifies review". The DCO certifies origin, not review: clause (a) says the contribution "was created in whole or in part by me", and clause (c) needs a person who received it from someone who certified it, which an agent cannot be. US copyright in code an agent wrote from prompts is also doubtful, which weakens the Apache-2.0 grant, the escrow, and D-ECO-22's premise that the kernel needs protection from relicensing. The spec names neither issue.
**Evidence:** D-ECO-21: "Agents never add `Signed-off-by`; agent-assisted commits carry `Assisted-by: <tool, model>`, and a human's sign-off certifies review." DCO 1.1 clauses (a) to (c) (https://developercertificate.org/). The US Copyright Office concludes that "Prompts alone, however, at this stage are unlikely to satisfy those requirements" of human authorship (Copyright and AI, Part 2, January 2025, https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf).
**Fix:** ECO adds a decision: "Agent-written commits carry `Assisted-by` and a founder `Reviewed-by`, never `Signed-off-by`. The project's licence notice states that portions may not be protected by copyright, and the patent grant and trademark policy carry the protection. Counsel gives a written opinion on authorship and the DCO before the phase 0 gate, and contract 13.1 lists it." External contributors keep the DCO unchanged.

### R17-18 · Major · Targets: CONTRACT, KLN, AGT, ECO
**Section:** Contract 13.1 phase 0 gate and 7.1 Anvil (freedom to operate)
**Problem:** The freedom-to-operate search covers only chains A and B (SSI, Booleans, blends, tessellation, implicit lattices), but phase 1 also ships versioning with branches and merges explicitly modelled on Onshape's microversions, agent Proposals with snapshot-based review, and STEP and 3MF writers. Each is a field where incumbents file patents. A product launched on GP1 with chain D in it carries unsearched risk exactly where it copies an incumbent's named design.
**Evidence:** Contract 13.1: "a freedom-to-operate search of the phase 1 code paths of chains A and B". D-KLN-19: "Edits become immutable Changes, as in Onshape's microversions". Onshape describes the same model: "The new microversion stores a reference to the previous (parent) microversion and the actual definition change" (https://www.onshape.com/en/blog/under-the-hood-how-collaboration-works). Specific patents on it are [unverified].
**Fix:** Change the gate item to "a freedom-to-operate search of every phase 1 code path in chains A to D, with KLN's Changes, branches, merge and live sync, AGT's Proposal and review flow and ECO's AP242 and 3MF writers named", and add the same search at each later gate for that phase's new capabilities.

### R17-19 · Major · Targets: CONTRACT, ECO
**Section:** Contract 2 and 13.1 (name clearance); ECO "Security, sanctions and notices"
**Problem:** Only "Crucible" is cleared and only "Flux" is renamed, yet Ingot, Anvil and Kiln are user-visible: a language with a file extension, and crate and package names. Kiln is the name of Fog Creek's commercial version-control and code-review product, the same goods as KLN's `repo`. The gate's logic, renaming before names freeze into WIT packages and crates, applies to all four.
**Evidence:** Contract 13.1: "names cleared (Crucible) or replaced (Flux)". The FogBugz help centre describes Kiln as "commercial hosting and support for people who use Mercurial" with code review (https://fogbugz.kayako.com/article/55180-general-information-kiln-and-version-control-products); whether it is still sold is [unverified].
**Fix:** Extend the phase 0 gate: "every user-visible name (Ingot and `.ingot`, Anvil, Kiln, and every crate, package and CLI name) is cleared in classes 9 and 42 or replaced; internal crate names carry the `crucible-` prefix on crates.io." List Kiln as at risk in ECO.

### R17-21 · Major · Targets: ECO, CONTRACT
**Section:** ECO D-ECO-33 "Strategy and exchange levels"
**Problem:** STEP layer 1 is on the phase 1 critical path, yet ISO's permission is asked only "before layer 1's first release", and the fallback breaks three principles at once. Per-organization generation gives each organization a different translator binary, so `OpKey`s differ and imports stop sharing caches. The open-source distribution cannot read STEP, and the desktop without a team server, which phase 1 supports, has no server to load the build from.
**Evidence:** D-ECO-33: "If ISO refuses, each organization generates layer 1 from its own copy, and browsers load that build from its team server." Contract 13.2 makes a "desktop install without a team server" a phase 1 mode.
**Fix:** Move the permission request into contract 13.1's phase 0 gate list beside name clearance. Make the fallback deterministic: "the steward publishes the generator and the expected binary hash for each pinned schema hash; any organization that holds the schema generates bit-identical layer 1, which the host accepts only at that hash", so `OpKey`s match everywhere, and desktops generate it locally from the user's copy.

### R17-22 · Major · Targets: KLN, ECO
**Section:** KLN "Data leaving a tenant"; ECO "Deterministic export"
**Problem:** The tabs promise that "any leaked file traces to its release" through a deterministic watermark that `crucible verify-watermark` recomputes. A recipient who re-saves a STEP file in any CAD tool, or re-slices a 3MF, removes marks held in comments, identifiers or ordering. Marks inside geometry would change what is made, which no release may do. A public, keyless transform also lets one recipient forge another's mark and frame them.
**Evidence:** KLN: "so any leaked file traces to its release". ECO: "`crucible verify-watermark` recomputes it, so any recipient's file traces to its release."
**Fix:** Restate as: "Watermarks deter casual redistribution and identify unmodified copies only. They are keyed with an HMAC under the tenant's watermark key, so recipients cannot forge each other's marks, and never alter definitional geometry or attributes. Traceability rests on the release-data record of who received which file hash." ECO-O-33 adds a re-export round trip that is reported as untraceable.

### R17-23 · Major · Targets: ECO, KLN
**Section:** ECO "Security, sanctions and notices" (C1 to C3 severities); KLN "Traceability and compliance"
**Problem:** The spec handles the CRA but not product liability, though Crucible sells `SignOff` verdicts that engineers release safety-critical parts on. The EU's new Product Liability Directive treats all software as a product and applies from 9 December 2026, inside phase 1, so a non-conservative result in a commercial distribution can bring strict-liability claims. How validity envelopes, `Undecided` verdicts and model-form allowances are presented to users then matters legally, and no tab addresses it.
**Evidence:** The European Commission states that "all types of software are covered by the new directive" and that it "will apply to products placed on the market as of 9 December 2026" (https://single-market-economy.ec.europa.eu/single-market/goods/free-movement-sectors/liability-defective-products_en). ECO's C1 severity already defines "A `SignOff` result is non-conservative".
**Fix:** Add to ECO: "Before phase 1 general availability, counsel assesses product-liability exposure under Directive (EU) 2024/2853 and US law for hosted and commercial distributions. The commercial terms, the product information shipped with each release (validity envelopes, the meaning of `Estimated` and conditional verdicts) and the C1 advisory process follow that assessment, and the program budget carries the insurance it recommends." Contract 13.1 lists the assessment at the phase 1 gate.

### R17-24 · Minor · Targets: CONTRACT, ECO
**Section:** Contract 7.7 "Registry"; ECO D-ECO-15
**Problem:** The contract says the registry uses "trusted publishing only", while ECO also lets "a person publish with phishing-resistant 2FA, as an audited Act". One of them is wrong.
**Evidence:** Contract 7.7: "trusted publishing only". D-ECO-15: "CI publishes through trusted publishing with a short-lived OIDC credential, or a person publishes with phishing-resistant 2FA".
**Fix:** Contract 7.7 reads "trusted publishing, or a person's publish Act approved with an approval credential", matching D-ECO-15.

### R17-28 · Minor · Targets: AGT, ECO
**Section:** AGT "MCP profile", "Roles"
**Problem:** A skill is instructions by design. The hosted crew loads another publisher's role only after `policy:admin` approval, but nothing stops `skills/list` from serving an unapproved third-party role skill to an external host, whose model then follows it. That contradicts D-ECO-32, under which third-party package text is `ExternalText`.
**Evidence:** AGT: "trust in approved role skills binds only the hosted crew", and "The hosted crew loads another publisher's role only after `policy:admin` approves its version and digest."
**Fix:** "`skills/list` and `skills/get` serve only std roles and roles whose version and digest `policy:admin` approved for the organization, to every host."

### R17-29 · Minor · Targets: ECO
**Section:** ECO "Names and namespaces"
**Problem:** Domain claims are "re-verified yearly", but the tab does not say what happens when verification fails. If the domain lapses and someone else registers it, re-verification by the new holder would hand them the namespace and its trusted-publisher policy, the expired-domain takeover known from package registries.
**Evidence:** ECO: "Domain claims re-verified yearly; transfers by consent or dispute policy, logged".
**Fix:** "A failed re-verification freezes the namespace: existing versions resolve, nothing new publishes, and only the previous owner key, or the dispute policy with evidence of continuity, unfreezes it. A new domain holder never inherits the namespace."

### R17-31 · Minor · Targets: KLN, ECO
**Section:** KLN D-KLN-34; ECO D-ECO-12 (Opaque references)
**Problem:** Events carry raw `ObjectId`s for `internal` content and opaque ids only above it. Webhook receivers are often third-party services, and a small `internal` record's `ObjectId` lets them confirm a guessed value, the R11-39 attack this rule was meant to stop.
**Evidence:** D-KLN-34: "above `internal` per-subscription opaque ids". ECO: "Above `internal`, payloads carry a per-subscription id".
**Fix:** Use per-subscription opaque ids for every label above `public`.

### R17-33 · Minor · Targets: ECO
**Section:** ECO D-ECO-21
**Problem:** The similarity scan compares contributions only against copyleft corpora. Agents also reproduce MIT, BSD and Apache-2.0 code, whose notices must ship, so an unattributed permissive snippet breaches the licence just as surely.
**Evidence:** D-ECO-21: "runs a similarity scan against copyleft corpora".
**Fix:** "...against copyleft and permissive corpora. A permissive match is allowed when the file carries the source's notice and the licence is on contract 7.7's list; a copyleft match blocks."

### R17-35 · Minor · Targets: ECO
**Section:** ECO D-ECO-16, D-ECO-22
**Problem:** The offline `claimed` role is "re-signed weekly" by the keyholders who hold the TUF root, at least half of whom are outside the company. A weekly threshold ceremony among outside root keyholders is an availability risk: one missed week expires the metadata and every client refuses claimed namespaces. It also exposes root keyholders weekly.
**Evidence:** D-ECO-16: "An offline `claimed` role, re-signed weekly by D-ECO-22's keyholders".
**Fix:** Give `claimed` its own offline threshold keys, held by the company's security staff, with a 90-day expiry and re-signing monthly. Root keyholders sign only root, which delegates to `claimed`.

### R17-36 · Minor · Targets: ECO, KLN
**Section:** ECO D-ECO-2 "Where translators run"
**Problem:** A licensed translation enters as a signed External input, but the tab does not say who signs it. When the translator ran on a user's desktop, the claim "translator X at version Y produced this from Asset H" is unverifiable by anyone without the licence, so substituted supplier geometry is indistinguishable from a real translation in an AS9100 audit trail.
**Evidence:** ECO: "Their output enters builds only as External inputs, pinned in the lockfile", with no signer named.
**Fix:** "A translator host signs each External input with a host key enrolled like a rig runner, recording translator version, licence id and input hash. Inputs without such a signature show as `Declared` provenance in review."

### R17-37 · Minor · Targets: ECO
**Section:** ECO D-ECO-29 (registry refusals)
**Problem:** The public registry refuses packages "whose label has `controls`", but a publisher who fails to label controlled technical data passes, and only paid packages declare an `export_classification`. Free packages are where an unaware engineer would post a controlled design.
**Evidence:** D-ECO-29: "The public registry refuses packages whose label has `controls`, and paid packages declare `export_classification`."
**Fix:** "Every public package version carries the publisher's attestation that it contains no technical data controlled under the ITAR or the EAR, or names the authorization for its publication. A DSA notice of controlled content quarantines the version pending review."

### R18-19 · Major · Targets: UIX, ECO, AGT
**Section:** UIX "Extending the interface" (`crucible:ui@0.1.0`)
**Problem:** The panel world returns a UI tree as `element`, a type that must contain child elements, but WIT forbids recursive types, so the package cannot be written as specified. The `use types.{…}` clauses also name an interface `types` that the package never declares.
**Evidence:** UIX: `render: func() -> element;   // element tree from data read through api`. The WIT specification: "Types, however, cannot be recursive" (https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md).
**Fix:** Declare `interface types` in `crucible:ui` with a flat tree: `record node { kind: node-kind, key: u64, parent: option<u32>, props: list<prop> }` and `render: func() -> list<node>`, nodes in pre-order with parents by index. Use the same arena form for `primitive-batch` if it nests. UIX-O-EXT-1 adds a published-WIT check that `wasm-tools component wit` parses the package.

### R18-31 · Minor · Targets: PLT, FLX, ECO
**Section:** PLT "Isolation and sign-in"; FLX D-FLX-9
**Problem:** From phase 1 the engine worker compiles Wasm at run time: user forms "compile to Wasm SIMD128 modules", and the first-party component runtime instantiates translator modules. Under any content security policy this needs `'wasm-unsafe-eval'` on the app origin, but PLT states CSPs only for the sandbox site, and ING mentions the need only for the phase 2 code generator.
**Evidence:** ING Platform notes: "pages allow `'wasm-unsafe-eval'`, without which 'WebAssembly is blocked'". D-PLT-42 gives the sandbox site's CSP; no row gives the main origin's.
**Fix:** PLT adds the app origin's policy: `default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' <team server>; frame-src <sandbox site>; object-src 'none'`. PLT-O-WEB-1 checks the served headers and that the engine worker compiles a user-form module under them.

### R19-03 · Major · Targets: MEC, CONTRACT, ECO
**Section:** MEC Packages (D-MEC-31); Holes and threads; Open questions 1
**Problem:** R11-30's fix created a new problem: thread series, clearance holes and fasteners are now licensed tables, and until counsel rules "an organization supplies its own table packages". The tab's own example, `ThreadSpec::iso_metric("M5")`, then fails with `UnknownSize`, since the coarse pitch of M5 comes from ISO 261. Every incumbent and the SolidCraft clone ship holes and threads that work on first use; Crucible's GP1, a machined bracket, needs them in phase 1, yet the decision waits until "before phase 1".
**Evidence:** MEC: "Thread plans, clearance holes, fasteners and steel sections are such tables"; Open question 1: "Kept open for counsel's review before phase 1 (D-MEC-31); until then an organization supplies its own table packages." MEC housing example: `HoleSpec::tapped(ThreadSpec::iso_metric("M5"), depth: 10mm)`. SolidCraft README lists "holes, threads" among its features.
**Fix:** (1) `std::standards::iso_metric_thread` and `unified_thread` accept full designations that carry the pitch (`"M5x0.8"`, `"1/4-20 UNC-2B"`) and compute every diameter and limit from the ISO 68-1, ISO 965-1 and ASME B1.1 formulas, with no table; a designation without pitch resolves through the series package, and its `UnknownSize` fix rewrites the call to the explicit form. (2) Clearance holes accept an explicit diameter or fit (`clearance(5.5mm)`, `H13`) without a table. (3) Make counsel's ruling on the series and fastener tables a phase 0 gate item in contract 13.1, beside the freedom-to-operate opinion, so GP1 never depends on a customer's tables.

### R19-10 · Major · Targets: ECO, MEC, UIX
**Section:** ECO Mechanical CAD and product data (DXF; DWG); MEC Drawings capability table
**Problem:** DXF waits for phase 2 and DWG for a licensed translator in phase 3, though shops quote, cut and archive from DXF and DWG every day. An open path exists: the acadrust crate reads and writes DXF R12 to 2018 and DWG R13 to 2018 under MPL-2.0, which contract 7.7 allows to link, and CADCraft already ships DWG through it. Crucible also has no stated way to make a 2D-only document (a layout, a plate drawn flat, an edited supplier DWG), which AutoCAD users and the CADCraft clone treat as basic.
**Evidence:** ECO: "DXF; DWG | DXF at phase 2 | R/W | … | Build; License | 2; 3"; MEC drawings row: "then DXF (2) and DWG through a licensed translator (3)". acadrust 0.4.1 (https://docs.rs/crate/acadrust/0.4.1): "MPL-2.0", "DWG Read/Write — Native binary, R13–R2018". Contract 7.7: "MPL-2.0 files may be linked" with notices and a source offer.
**Fix:** Move DXF write of drawing sheets and planar sections to phase 1, and DXF and DWG read and write to phase 2 through acadrust (linked under 7.7) or an own codec with acadrust as the oracle; the licensed translator becomes the fallback for versions acadrust lacks. In MEC, state that a drawing may hold 2D-only sheets: sketch geometry, layers as attributes, blocks as Ingot functions, hatches and dimensions, with an imported DWG becoming an editable drawing program through an import expression, as for 3D Assets.

### R19-17 · Major · Targets: KLN, ECO
**Section:** KLN Items, revisions and BOMs; ECO Migration from incumbent tools
**Problem:** Adopting teams keep SOLIDWORKS, Creo or NX files for years beside Crucible designs, and Teamcenter and Windchill manage those files with their reference structure and where-used. Crucible stores them as opaque Assets: a SOLIDWORKS assembly's references to its parts are invisible, so where-used, change impact and release completeness stop at the Asset. Subordinate mode covers the opposite case, Crucible releasing into an enterprise PLM.
**Evidence:** Siemens, Teamcenter MCAD design management (https://www.siemens.com/en-us/products/teamcenter/solutions/mcad-mechanical-design-management/): "easy to use with AutoCAD, Inventor, CATIA, Creo, NX, Solid Edge and SolidWorks", "All components can be incorporated into multi-CAD assemblies". ECO migration rows move geometry and history, not live native files; KLN's where-used indexes Crucible usages and `Purchased` Items only.
**Fix:** State a scope decision in KLN. Recommended: native foreign CAD files are `Document` Items with a reference graph that ECO's licensed readers extract at import (the assembly's referenced files and their configurations), so where-used, impact and release completeness cover them; Crucible never edits them. Otherwise say plainly that managing live foreign CAD files is out of scope and that subordinate mode or a separate PDM keeps them.

### R20-06 · Major · Targets: ECO, FLX, COV
**Section:** ECO format catalog ("Nastran BDF; Abaqus input"); FLX "Interfaces with other subsystems"
**Problem:** ECO reads and writes Nastran BDF and Abaqus input at phase 3 as "FE models; OP2 results as Fields", but no tab says what Crucible does with an imported deck: Flux has no element semantics for CQUAD4, CBUSH, RBE3, CONM2, PCOMP, MPCs or SPCs on grid ids, so a company's validated legacy models can be viewed but not run or compared. The export direction matters as much: aerospace and defence customers deliver Craig–Bampton models as Nastran DMIG or OP4 for coupled loads analysis, and some regulators expect the qualified incumbent's run. LS-DYNA keyword decks, the crash and drop lingua franca, are absent.
**Evidence:** ECO line 224; Ansys documents a mapping of its own model to SOL101, SOL103, SOL109, RBE2, RBE3, CBUSH and CONM2 (https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb_sim/ds_NASTRAN_export_supported_features.html), showing that deck export with idealizations is what users expect.
**Fix:** FLX adds "Imported FE models" with a contract: an imported deck becomes a `Mesh` Body plus a study whose cards map to Flux forms and R20-01's idealizations; unmapped cards fail with `UnmappedCard { card, line }`, never dropped. Oracle FLX-O-DECK-1: the NAFEMS decks distributed for Nastran verification run in Crucible within 1% of their reference values. Add export of a study to BDF (SOL 101, 103, 111, 112) and of Craig–Bampton reductions as DMIG and OP4, phase 3, so an incumbent can re-run a Crucible model. ECO adds LS-DYNA keyword read for meshes, parts, materials and contacts at phase 3 with GP5's drop model. The deck route is labelled `Unverified` until its oracle passes per card family.

### R20-15 · Major · Targets: ELX, FLX, ECO
**Section:** ELX "Co-simulation"; FLX "Networks"
**Problem:** Modelica users bring their models as source: the Modelica Standard Library and commercial libraries. ELX accepts Modelica only as compiled FMUs and leaves Rumoca as a phase 5 option. So a Dymola user cannot edit, version, diff or optimize their models in Crucible, cannot use Crucible's adjoints through them, and needs a second tool to build each FMU. Since Crucible's Network compiler already does Pantelides with dummy derivatives, BLT and tearing, the missing piece is a front end, not a solver.
**Evidence:** ELX line 681 ("Modelica arrives through FMUs"). Dymola is built on "an object-oriented language for physical modeling" with multi-domain libraries (https://www.3ds.com/products/catia/dymola). The Modelica Standard Library is v4.1.0 and spans mechanical, electrical, magnetic, thermal, fluid and control components plus state machines (https://github.com/modelica/ModelicaStandardLibrary).
**Fix:** ECO adds a Modelica reader as an `io/` Wasm component (Rumoca or a clean-room parser) that translates a declared subset (equation sections, connectors with flow and stream variables, `inner` and `outer`, records, replaceable classes) into `network { … }` Ingot, phase 4 for GP6. Unsupported constructs stay as an FMU fallback with `Untranslated { construct }`. Oracle: the MSL's `Modelica.Electrical`, `Mechanics.Rotational`, `Mechanics.Translational` and `Thermal.HeatTransfer` examples translate and match MSL reference results within their tolerances. ELX states the translation coverage as a percentage of MSL example models (target: 80% by phase 5).

### R20-23 · Minor · Targets: ELX, ECO
**Section:** ELX "Creating and migrating catalog parts"; ECO D-ECO-31, "Migration from incumbent tools"
**Problem:** Both tabs route proprietary ECAD through "KiCad 9's importers" (Altium, CADSTAR, EasyEDA, P-CAD, Fabmaster). KiCad 10 adds direct importers for Allegro and PADS, the two Cadence and Siemens formats whose users most need a migration path, plus gEDA and Lepton.
**Evidence:** "KiCad 10 can now import designs from Allegro, PADS, and gEDA / Lepton PCB" (https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/).
**Fix:** Pin KiCad 10 in the migration container. Name Allegro and PADS in ELX's step 2 and in D-ECO-31, and add an Allegro and a PADS design to ECO-O-25's corpus (netlist equality, empty Gerber XOR).

### R21-02 · Major · Targets: ING, FLX, COV, KLN, MFG, ELX, AGT, UIX, PLT, MEC, ANV, ECO, CONTRACT
**Section:** Every design section's decisions; "Open questions"; "Contract change requests"; contract lead
**Problem:** The tabs read as the minutes of their own revision. Review finding ids appear as evidence inside running prose, decisions end in "(revised in round N)", "Rejected" clauses name "the round 2 rule", and "Open questions" sections list declined findings rather than open questions. A reader who was not in the review cannot use any of it, and the Adversarial review tab already owns this history.
**Evidence:** Counted before each tab's "Open questions": finding ids such as "(R3-37, R9-40)" appear 112 times in PLT, 62 in FLX, 56 in MFG and AGT, 48 in ELX, 45 in UIX, 43 in KLN, 34 in COV and 26 in ING (482 in all), while ANV, MEC and ECO show that a tab reads well without any. "(revised in round N)" appears 235 times across twelve tabs. Examples: D-ING-7 "*Rejected:* … `Pending` and `ING6401` as node values, the round 2 rule. (revised in round 3)"; D-MEC-26 "*Why:* … the round 1 drafts claimed the formboard twice"; D-FLX-1 "*Rejected:* the round 1 seven-crate split"; MEC "It replaces `crucible:model`"; KLN "`crucible:product`, formerly `crucible:model`". ING's "Open questions" opens "This revision decides all nine round 2 questions" and then lists ten bullets of declined findings; MEC's question 2 and AGT's question 2 are titled "Findings declined…". The contract's lead is a version history.
**Fix:** One mechanical pass, then a rule. (1) Delete every finding id from text above "Open questions"; where the id stood in for a reason, write the reason ("a policy-clamped limit made two organizations cache different results for one key" stays, "(R3-12)" goes). (2) Delete every "(revised in round N)"; the Decisions log and `git log` keep revision history. (3) Delete "the round N rule", "formerly", "replaces" and similar history from decisions and names; a rejected alternative is described by what it is. (4) "Open questions" holds only unresolved questions; move every "Findings declined or applied in part" list to the Adversarial review tab under that tab's code. (5) "Contract change requests" holds only open requests or "None"; accepted ones are recorded in the contract's ruling log. (6) The contract's lead is one sentence: "Binding for every design agent and reviewer; where a tab disagrees with it, the contract wins." Add to `check.py` a rule that fails on `\bR\d{1,2}-\d{2}\b`, "revised in round" and "round \d" outside the Adversarial review and Decisions log tabs.

### R21-08 · Major · Targets: CONTRACT, COV, KLN, MFG, AGT, ECO, OVERVIEW
**Section:** Contract section 2 ("Evidence record", "Evidence level"); COV "Evidence levels"
**Problem:** "Evidence" names at least six things: an Evidence record (a signed physical measurement), an evidence level (a model's credibility, E0 to E4), the evidence watermark (a log position), the `evidence_records` field of `CheckOutcome`, "simulation evidence" for manufacturing programs, and "sampled evidence" for query stability, plus "licence evidence" and "oracle evidence". The contract notices the clash ("Distinct from an Evidence record"; "'evidence' never names a bound kind") but keeps it. A reader of "E3 evidence" next to "Evidence records from the proof load" cannot tell a model property from a measurement.
**Evidence:** Phrase counts across the contract and tabs: "simulation evidence" 6, "evidence levels" 5, "licence evidence" 4, "oracle evidence" 3, "sampled evidence" 2, besides 15 uses of "Evidence record(s)". Contract 5: "`ApprovalSubject` … `evidence record ids`"; contract 7.6: "the posted program and its simulation evidence"; contract 5 (`Query`): "Stability … is sampled evidence".
**Fix:** Rename the evidence level to the **credibility level**, C0 to C4 (Declared, Verified, Benchmarked, Validated, Context-qualified), the term ASME V&V 40, which COV already cites for E4, uses for this idea. Reserve "evidence" for Evidence records and the watermark over them. Replace the other uses: "simulation results" for manufacturing programs, "sampled stability" for queries, "licence proof" for ABC per-model records, "oracle results" for CSA packages. Contract section 2 rows: "**Credibility level** · How well a physics model has been tested against reality, C0 to C4 (COV) · 'evidence level'"; add "credibility level" to the Evidence record row's "Never call it" column. This is a contract change; COV files it.

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

### R21-26 · Minor · Targets: ING, ANV, FLX, COV, KLN, MEC, MFG, ELX, AGT, UIX, ECO, PLT, CONTRACT
**Section:** Capability tables at the end of each design section
**Problem:** Capability tables are the build contract, but in reading order they arrive as a dense block after every section, and many cells add nothing: "Failure: —" and "Not expressible" stand where the reader expects a typed failure. The published doc gives them the same weight as explanation.
**Evidence:** ING "Purity | … | Not expressible"; MEC "Typed failures and fixes | `FeatureError { kind, why, fix, at }` | —"; AGT "Priority classes | … | — ".
**Fix:** Replace "—" with "None: cannot fail" or the actual failure, and "Not expressible" with "None: the language cannot express a violation". In the published doc, render capability tables as a visually distinct, collapsible "Build contract" block under each section, so a reader can follow the prose without the tables breaking it.

## Claims the reviewers verified

Drop the `[unverified]` marker on these and cite the URL in Sources.

None in this review.

## Unverified claims in your tab

Verify each with WebFetch on a primary source and drop the marker, correct it, or cut the claim if nothing supports it. Line numbers are at tag `round-3`.

None.

## Your open questions

Close each: decide it (the reviewers propose answers above), move it to a contract change request, or keep it with the reason it cannot be decided yet.

1. **Translator vendor.** Kept. The choice among CAD Exchanger, HOOPS Exchange and Datakit depends on terms only negotiation reveals. They cover server use, unlicensed rebuilds, ARM64 builds and offline activation. The founder signs the first agreement before the phase 2 gate.
2. **CAx-IF terms.** Closed: round files enter `oracles/` only where the forum's terms allow, and the fee is a phase 1 budget line.
3. **EXPRESS sources and `espr`.** Closed by D-ECO-33 and the fork of `espr`'s parser.
4. **OSV ecosystem.** Closed: a pull request registers `Crucible` in phase 1, and correctness advisories carry `database_specific.kind = "correctness"`.
5. **Foundation.** Closed by D-ECO-22: an existing foundation with a recorded trademark option.
6. **Marketplace terms.** Closed by D-ECO-19: the steward is merchant of record, and the founder sets the fee level when paid packages open.
7. **ODB++ terms.** Closed: counsel reads the partnership terms before the phase 3 writer starts. If they forbid Apache-2.0, the writer ships as an external tool.
8. **iPadOS.** Closed by contract section 7.4: registry components evaluate remotely.
9. **CVE identifiers.** Closed: OSV and code-host ids, then numbering-authority scope once the public registry opens.
10. **Test corpora.** Closed by D-ECO-37 and contract section 13.3.
11. **Component Model.** Closed: the re-encoding rule covers encoding changes, and 64-bit memories wait for every Tier 1 browser engine.
12. **Findings declined or applied in part.**
    - R4-29, R4-09, R4-10 (round 2): board import and NC and tool-data migration stay in phase 2. Contract section 13.2 limits phase 1 to GP1 and GP2.
    - R5-25 (round 2): no foundation at phase 0 (contract section 7.7); the backstop, trademark option and key ceremony bind the trigger.
    - R11-29: applied, but its premise about the steward's size no longer holds (contract section 13.2); Articles 20 and 30 are adopted by choice.
    - R11-32: the permission request is due "before layer 1's first release" rather than by a calendar month, since milestones are ordered, not dated.
    - R11-49: CNA scope follows the public registry's opening, since the program has no human team (contract section 13.2).
    - R11-45, R11-28, R9-47: applied here and in contract 13.1, 7.7 and 7.6 (CCR-ECO-12, CCR-ECO-10, CCR-ECO-11).
    - R9-26: ECO keeps a short table of its own four packages beside the index.
    - R8-23, R11-33: ECO applies its part (D-ECO-37); MEC, ANV and AGT own the rest.

## Known items

- Read `docs/revision/digest.md`: adopt the permissive libraries that serve your tab, name copyleft tools only as oracles, and use the clean-room insight protocol of contract 7.7 for incumbent behaviour.
- Add one sentence under each drawn diagram that tells the reader how to read it (`diagrams/11-interop-translation-flow.jsx`, `diagrams/11-interop-publish-pipeline.jsx`).
