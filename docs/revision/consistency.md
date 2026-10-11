# Round 2: consistency pass (brief for each tab's agent)

All twelve subsystem tabs are v2, and contract v5 has ruled on every change request (contract section 16). Your job: make your tab agree with contract v5 and with the other tabs, without reopening the revision. Edit only your own `docs/spec/<file>.md`; never edit another tab, the contract, a README or CLAUDE.md, and never commit.

## 1. Read

1. Contract v5's changes: `git diff round-1 -- docs/contract.md` is long, so read section 16 (the ruling log) and the sections it cites, plus 13.4 (shared phases).
2. Your own tab in full.
3. `docs/build/extracts/interfaces.md`: every tab's "Interfaces with other subsystems" section. When you compare against another tab, use its committed text (`git show HEAD:docs/spec/<file>.md`), because other agents are editing their working copies now.

## 2. Make it consistent

- **Change requests.** Every request is ruled. Replace your "Contract change requests" section with one line per request you filed: its id, "accepted in contract v5" (or v4.1, v4.2) and the section that now holds the rule. Body text that cites a CCR as pending cites the contract section instead.
- **Phases.** Every shared capability uses its phase from contract 13.4, in capability tables, prose and the Phasing section. Cite 13.4 once in Phasing.
- **Names.** Use the glossary (contract 2), including v5's additions: Item, Model level, Evidence level, the physical-effect Acts (`send_to_machine`, `send_robot_program`, `store_machine_job`, `send_print_job`, `start_print`, `run_rig_test`), `RenderProfile`, and `Budget` and `PriorityClass` owned by AGT.
- **Oracle ids.** Round 2 renamed oracle ids: `O-AGT-n` is `AGT-O-n`, `O-ECO-n` is `ECO-O-n`, `cov/*` became `COV-O-*`, `uix_*` became `UIX-O-*`, and KLN and PLT oracles gained `KLN-O-*` and `PLT-O-*` ids. Update every citation of another tab's oracle to an id that tab defines now.
- **Interfaces.** Each row of your "Interfaces with other subsystems" must match the other tab's row about you. Where they disagree, the owner of the fact wins: the tab named in the contract's `[TAB]` tags, or the tab whose design section specifies it. Change your side only when you are not the owner. If ownership is unclear, leave the text and report it.

## 3. Rulings on known disagreements

These were reported by the revision agents; the orchestrator has decided them.

| Topic | Ruling | Tabs that change |
| --- | --- | --- |
| Default tolerance distribution | MEC owns it (D-MEC-28): `std::mech::tol::default_distribution`; ISO 286 tables are `std::standards::iso286` | ING |
| IDF and STEP board import | ECO owns format readers: phase 2, on an early 1.x train (contract 13.2 keeps phase 1 to GP1 and GP2) | ELX, MEC |
| `crucible:ui` WIT names | UIX owns them: interfaces `types`, `view`, `canvas-host`, `canvas`; worlds `panel`, `canvas2d` | ECO |
| Format writers, ODB++ included | ECO owns every writer and its phase; MFG chooses output packages; ELX defines board data and points to both | ELX, MFG |
| Transfer and start Acts | Contract 7.6 names only (no `transfer_program`, `start_build`, `queue_program`) | MFG, AGT, KLN, ECO, UIX |
| Manufacturing change orders and the `Program` Item kind | KLN owns change orders (D-KLN-38); a manufacturing program is an Item (contract 2) | MFG, KLN |
| Characteristic balloons and weld quality levels | MFG allocates labels (D-MFG-26); MEC draws them and records the weld quality level on `Weld` | MEC |
| Definition digests with late-bound revision text | KLN adds them for ELX's library parts | KLN |
| Electronics canvases | UIX (D-UIX-27) | none |
| Flux phases | Electro-thermal coupling and FMU export with SSP move to phase 4, DFN cells to phase 5 (13.4) | FLX |
| Anvil and Flux citations | CCR-ANV-7, CCR-ANV-8, CCR-FLX-8 and CCR-FLX-9 are accepted (13.3, 5, 5, 13.4) | ANV, FLX |

## 4. Check and report

Run `python3 docs/tools/check.py docs/spec/<file>.md --base round-1`; it must report zero errors, and no decision, oracle or source may be cut. Reply in at most 200 words: what you changed, which interface rows you aligned and to whom, anything you left for the orchestrator because ownership was unclear, and the check result.

## 5. Follow-up rulings

The first pass surfaced these mismatches. The owner wins; each line says what the named tab changes. Apply only your tab's lines, keep every decision, oracle and source (revise a decision in place and end it with "(revised in round 2)"), stay within the word limit, and run the check.

| Tab | Change |
| --- | --- |
| ANV | The AGT interface row includes measures, sections and `RankSwap`, which AGT requires. |
| FLX | Mode-shape display lands in phase 1 with modal analysis (13.4); split FLX-O-POST-1's row if needed. FLX defines manufacturing-constraint forms itself and requires MFG's process profiles (overhang angle, build and draw direction, minimum feature size). Any requirement for "`param` marks" from ING becomes ING's feature parameters. |
| COV | COV states which zones are extrapolated; their display is UIX's hatching. Drop the amber overlay and point to UIX. |
| KLN | Revise D-KLN-40: AGT owns the `release_data` Act family (D-AGT-30); KLN runs that stage at commit and records it. Revise D-KLN-44 to point to PLT's one engine per browser origin (D-PLT-29). Events deliver from phase 1, with ECO's webhooks. The FIPS-mode crypto provider is required from PLT. The `api` table matches AGT on agent Proposals. |
| MEC | MEMS masks come through ANV's `anvil-planar` and ECO's GDSII and OASIS writers, not ELX. The FLX interface row includes redundancy reports (D-MEC-12) and default distributions (D-MEC-28). |
| MFG | Heat-treatment distortion uses COV's phase-transformation models, so it lands in phase 6. PBF thermo-mechanics follows COV: phase 4. MTConnect reads follow ECO: phase 3. Passport publication is phase 3, matching AGT. Solidification and current distribution come from COV physics packages built on Flux forms; receptance coupling for stability lobes is MFG's own model from measured FRFs. G-code comes from MFG's post engine through the `crucible:mfg` post world. Partner quotes follow ECO's phase 2. Record the machine gateway under Open questions as a round 3 contract request: the crate map has no gateway app. |
| ELX | ELX owns lumped drivetrain Network elements (gear ratio, mesh stiffness, couplings, bearing friction), parameterized from MEC's gear records; add them to the networks capability table if missing and stop crediting MEC. "Timeline viewer" becomes UIX's chart viewers and recorded sessions. STEP body import comes from ECO's readers, not ANV. The COV row includes battery swelling and abuse mechanics (13.4). Record firmware flashing outside `unattended_safe` rigs under Open questions as a round 3 contract request: contract 7.6 names no Act for it. |
| AGT | D-AGT-30 owns `release_data`; state that KLN runs it at commit (D-KLN-40). The stdio sandbox for external MCP servers is required from PLT. Registry method names match ECO's current text. |
| UIX | Phase 1 `DisplayPackage`s carry level-0 clusters from ANV's tessellation; cluster-DAG pages arrive in phase 2 (contract 13.2), and no row expects them in phase 0. Device loss follows PLT's threshold of 3 in 10 minutes. |
| ECO | The event sequence attribute is `sequence`, as the CloudEvents sequence extension names it. Add writer rows for PDF, SVG and PDF/A (phase 1, GP1 drawings), DXF (phase 2) and DWG (phase 3), and a KBL row. Wasm component seeds: Ingot passes an explicit `seed` from an `Rng` (ING owns randomness), so ECO points to ING. Third-party panels run out of process (7.4), not "in the app". G-code comes from MFG's post engine; list the `crucible:mfg` worlds MFG defines and drop any separate G-code writer. Events deliver from phase 1. |
| PLT | PLT provides the FIPS-mode crypto provider KLN needs and the stdio sandbox AGT needs; add both to the provided rows if missing. Add an MFG interface row. Record the machine gateway under Open questions as a round 3 contract request. |
