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
