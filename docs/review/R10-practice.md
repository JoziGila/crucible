# R10 engineering practice review

Summary: Transfer Acts can still start devices: OctoPrint, Moonraker, PrusaLink and Universal Robots interfaces carry a start inside the upload or transfer channel, which the static "no start method" oracles cannot see, and drip feed into a control already waiting for data starts motion when the Act commits (R10-01, R10-02).
The phase 1 gate cannot be judged inside Crucible. GP1 is "measured by external metrology against Crucible's tolerances", but characteristics, balloons, results import and decision rules all land in phase 2 or 3 (R10-03).
The shop-floor path is specified as push transfers. Each needs its own approval over instance data (machine serial, tool pockets), and the path has no program-number control, restart points, wear compensation or control-resident macros, so the gateway as written is either unsafe or unusable in a real shop (R10-08 to R10-15).

### R10-01 · Critical · Targets: CONTRACT, MFG, AGT
**Section:** MFG "Approval, transfer and physical safety" (Act table, MFG-O-SAFE-3); AGT D-AGT-31 and AGT-O-21; contract 7.6 Physical safety
**Problem:** The guarantee that a transfer never starts a device rests on static oracles. MFG-O-SAFE-3 passes when connector WIT worlds "expose no motion or start method (the static interface is the product boundary)", and AGT-O-21 passes when "no Act plan schema can express a machine start". In the protocols MFG targets, though, the start sits inside the upload call itself: a flag, a header or a choice of port. A connector whose interface is pure "upload" can therefore start a print or move a robot, and both oracles pass. R4-01's fix holds at the interface but not on the wire.
**Evidence:** OctoPrint's upload endpoint takes `print`, "Whether to start printing the file directly after upload" (https://docs.octoprint.org/en/master/api/files.html). With Moonraker's `print` set, "Moonraker will command Klippy to start the print after the upload has successfully completed" (https://moonraker.readthedocs.io/en/latest/external_api/file_manager/). PrusaLink's PUT upload takes a `Print-After-Upload` header, "Whether to start printing the file after upload" (https://raw.githubusercontent.com/prusa3d/Prusa-Link-Web/master/spec/openapi.yaml). Universal Robots' client interfaces "receive URScript commands" and make it "possible to control robot remotely without robot program" (https://www.universal-robots.com/articles/ur/interface-communication/overview-of-client-interfaces/). MFG names OctoPrint, Moonraker and PrusaLink for `send_print_job` and URScript among its robot posts.
**Fix:**
1. Replace MFG-O-SAFE-3's pass criterion with a behavioural one. Each connector runs against the real server or the vendor simulator (OctoPrint; Moonraker with a Klipper simulator; PrusaLink; URSim; each controller simulator) under wire capture. It passes when no request carries a start semantic and the device stays idle after every transfer. Start semantics include OctoPrint `print` or `select` set true, Moonraker `print` true, PrusaLink `Print-After-Upload`, Bambu MQTT print commands, any URScript to the primary, secondary or real-time interfaces, and Dashboard Server commands.
2. Each connector manifest declares an allowlist of endpoints with fixed parameter values. The gateway enforces it in its own egress filter, outside the Wasm connector, so a defective or malicious connector cannot add a flag.
3. Robot programs transfer only as program files into the controller's program store, never through script or dashboard interfaces (transport per vendor [unverified]).
4. AGT-O-21 adds the same wire-level criterion. Contract 7.6 adds one sentence: "Transfer Acts are verified at the protocol level; an interface that cannot express a start is necessary, not sufficient."

### R10-02 · Critical · Targets: CONTRACT, MFG
**Section:** MFG "Approval, transfer and physical safety" (DNC and drip feed row; `send_to_machine` rule); contract 7.6 Physical safety
**Problem:** `send_to_machine` "Delivers a program to a control's memory or DNC queue" and "Never selects, loads or starts it", and MFG ships serial and Ethernet drip feed in phase 2. In drip feed the control executes blocks as they arrive. A control left in tape or remote mode with cycle start pressed waits for data. When the approved Act commits and the gateway starts streaming, axes and spindle move at commit time, perhaps hours after the button press and with nobody at the machine; the approver may be remote. Contract 7.6's "a person starts them at the device" does not hold on this path.
**Evidence:** The stated mechanism ("Serial DNC with XON/XOFF or RTS/CTS flow control, and Ethernet DNC") lets the control pace execution by requesting data, so the commit is the first event that supplies it. MFG-O-SAFE-5 ("Drip feed against controller simulators stops and reports every injected fault") tests faults during a feed, never a control that was waiting before the commit.
**Fix:**
1. Drip feed is pull-only. `send_to_machine` stages the approved program in the gateway's per-machine DNC library and sends nothing.
2. The gateway streams only in response to a request made at the control: a DNC remote request naming the staged program, or the control's data request. The request must begin after the commit and after an on-site confirmation entered on the gateway's machine-side terminal.
3. If the control already has a data request or DNC session open when the Act commits, the gateway refuses with `DncSessionPreArmed` and asks the operator to reset and request again. It never sends unsolicited data to a control in tape, remote or DNC mode.
4. MFG-O-SAFE-5 adds simulator cases waiting for data at commit, with a pass criterion of zero bytes sent in 100% of them.
5. Contract 7.6 adds: "A transfer never completes a start the device was already waiting for."

### R10-03 · Major · Targets: MFG, MEC, KLN, ECO
**Section:** MFG "Inspection and measurement" and "Quality records" (phases); MEC "Revisions, balloons and generated drawings"; KLN "Physical tests and Evidence records"; ECO QIF row; MEC Open questions 9 (R4-14)
**Problem:** The phase 1 gate measures GP1 "by external metrology against Crucible's tolerances", but every piece that turns lab readings into a verdict on a tolerance lands later:
- characteristic identities and balloon labels (MFG and MEC, phase 2);
- QIF characteristics (ECO, phase 2);
- results as Evidence records (MFG, phase 3);
- uncertainty-based conformance decisions (MFG, phases 2 and 3).

KLN admits lab Evidence records in phase 1 "addressed by the check it serves", but a GD&T control has no check until MFG creates its characteristic. MEC's partial decline of R4-14 ("phase 1 drawings carry item balloons only") rests on a wrong premise, because the phase 1 gate itself needs characteristic balloons.
**Evidence:** Contract 13.1 phase 1 gate. MFG rows "Characteristics and balloons ... 2", "Results as Evidence records ... 3" and "Uncertainty budgets and decisions ... 2, 3, 4". KLN: "In phase 1, external metrology for GP1 and GP2 enters as Evidence records signed by the lab's principal."
**Fix:** Move a minimal inspection loop to phase 1, scoped to GP1 and GP2:
1. D-MFG-18 characteristic extraction and D-MFG-26 labels for size, location, orientation, form and profile controls.
2. MEC's characteristic balloons and the ballooned PDF.
3. A results import from QIF 3.0 Results, plus a CSV template keyed by balloon label for labs without QIF output, creating one Evidence record per characteristic.
4. One conformance check per characteristic using the ISO 14253-1 default decision rule [unverified edition] with the lab's stated expanded uncertainty: `Pass`, `Fail`, or `Undecided` inside the guard band.

CMM programming, SPC and AS9102 stay in phases 2 and 3. Contract 13.2's "DfAM and cost 0 → 2" or "features, sketches, drawings and GD&T 2 → 6" line absorbs the work.

### R10-04 · Major · Targets: CONTRACT, MFG, AGT
**Section:** Contract 2 (Act) and 7.6 Physical safety; MFG Act table; MFG rows for CMM programs, press brakes, heat treatment, reflow and harness packages
**Problem:** The physical-effect Acts are a closed list, and the machine transfer is "`send_to_machine` (an NC program)". MFG also generates programs for devices that are not NC machine tools in that sense:
- CMM part programs;
- press-brake bend programs;
- heat-treatment and reflow recipes;
- SMT placement programs;
- harness cut-and-crimp job lists;
- molding-machine setups.

None has a transfer Act. They leave through data-release Acts or on a USB stick, which bypasses the gateway's hash, read-back, offset and numbering checks, and the never-start rule does not name CMMs, press brakes, ovens or placement machines.
**Evidence:** Contract 2: "Physical-effect Acts are the transfer Acts `send_to_machine`, `send_robot_program`, `store_machine_job` (OPC UA `Store` only) and `send_print_job`". Contract 7.6: "`send_to_machine` (an NC program)". MFG: "CMM paths and programs | Collision-free paths with articulating heads; DMIS and QIF Plans"; "Press-brake planning"; "Heat treatment and HIP | Recipes"; "Panels, stencils and reflow".
**Fix:**
1. Contracts 2 and 7.6 redefine `send_to_machine` as "a program or recipe for any device reached through the machine gateway". Its payload is typed as `NcProgram | DmisProgram | BendProgram | Recipe | PlacementProgram | CutList`, each with a device class.
2. The never-start list becomes: machine tools, CMMs, robots, lasers, presses and press brakes, furnaces and ovens, placement and harness machines.
3. Every payload kind gets D-MFG-24's digest, read-back where the device supports it, and R10-11's number registry.
4. AGT's Act table and AGT-O-21 follow.

### R10-05 · Major · Targets: CONTRACT, MFG, AGT, UIX
**Section:** Contract 7.6 Physical safety (`start_print`); MFG "Printers, 3MF and print transfer"; AGT D-AGT-31
**Problem:** `start_print` rests on four weak conditions.
1. The safety declaration lives in a printer profile, which is a registry package from a third party, so it is self-declared. `unattended_safe`, by contrast, needs a safety officer's signed site policy.
2. "Enclosure or smoke detection" accepts an enclosure without detection, which contains nothing when the enclosure is plastic.
3. Nothing restricts the process, so a laser powder-bed machine with such a profile qualifies, although contract 7.6 says Crucible never starts lasers or furnaces.
4. "A site-bound key" lets someone confirm a clear build plate from anywhere on site without seeing it.
**Evidence:** Contract 7.6: "`start_print` exists only for printers whose profile declares thermal-runaway protection and enclosure or smoke detection, and needs an Approval of the job digest plus an on-site confirmation that the build plate is clear, given at the printer or with a site-bound key." MFG: "Printer profiles are packages".
**Fix:** Contract 7.6 replaces the rule:
1. `start_print` exists only for material-extrusion printers and for vat-photopolymerization printers whose light source is not a laser above Class 1 [unverified classification per model]. It never applies to powder bed fusion, directed energy deposition, binder jetting or any printer that needs inert gas.
2. Each printer serial needs a signed site policy from the named safety officer. The policy declares firmware thermal-runaway protection and smoke or heat detection that cuts printer power.
3. The on-site confirmation is given at the printer, within 10 minutes before the start. It uses a printer-side button where the firmware offers one, or a one-time code shown on the printer's display and typed into the confirmation.

MFG-O-SAFE-2 seeds profile-only declarations, laser-process printers and confirmations from elsewhere on site, and all must be refused.

### R10-06 · Major · Targets: CONTRACT, ELX, AGT, KLN
**Section:** ELX Open questions 13; ELX "Hardware-in-the-loop"; ELX Platform notes ("Hardware access")
**Problem:** ELX leaves open whether flashing a board outside an `unattended_safe` rig is an Act. Its Platform notes already let clients flash through `apps/platform`, and browsers through WebUSB. Flashing is a physical effect: firmware runs when the core leaves reset. Flashing a motor controller, ESC, heater driver or charger therefore starts motion or energy at that moment, which is what contract 7.6 reserves to a person at the device. GP6 (ESCs and flight controller) and GP12 (BMS and charger) depend on flashing.
**Evidence:** ELX: "on any other bench a person flashes the board and enables outputs". ELX Platform notes: "Bench adapters and flashing use USB and serial through `apps/platform`; browsers use WebUSB and WebSerial where available".
**Fix:** Answer to ELX OQ13. Flashing becomes a transfer Act, `flash_device`, in contract 2's list.
1. Its plan names the Software item version, image digest, target board serial and the probe or bootloader.
2. The bench adapter or gateway writes the image, verifies it by reading back its digest, and leaves the target halted or held in reset. A person at the bench releases reset or applies power.
3. The Approval covers the image digest and target. The approval page shows the board's hazards from its Network (rotational ports, heaters, high voltage) and a "remove propellers and loads" step where they exist.
4. Client-side flashing through `apps/platform` and WebUSB is the same Act, never a side path. `run_rig_test` keeps covering flashing on `unattended_safe` rigs.

### R10-07 · Major · Targets: CONTRACT, KLN, AGT
**Section:** Contract 7.1 Hardware CI; contract 2 Act; KLN D-KLN-35
**Problem:** Two lists disagree. Contract 7.1 withholds `unattended_safe` only from "machine tools, robots or lasers", while contracts 2 and 7.6 say Crucible never starts "machine tools, robots, lasers, presses or furnaces".
- A servo-hydraulic load frame (a press) or a climate chamber (a furnace) may therefore carry the site policy yet never be started, though these are the rigs labs most often run unattended.
- Battery cyclers and abuse rigs for GP6 and GP12, the highest-energy tests in the plan, appear in neither list.

A list of device types is the wrong shape for this rule.
**Evidence:** Contract 7.1: "it is never granted to machine tools, robots or lasers". Contract 2: "Crucible never starts machine tools, robots, lasers, presses or furnaces".
**Fix:** Put one rule in contract 7.1, cited by sections 2 and 7.6.
1. Production equipment (machine tools, robots, lasers, production presses and furnaces, and every device class in R10-04) never receives `unattended_safe`.
2. A test rig may receive it only when the named safety officer signs a risk assessment to ISO 12100 [unverified edition] covering the rig and the test article. The rig also needs interlocked guarding and its own safety-rated stop.
3. The runner enforces declared energy limits locally: force, displacement, temperature, voltage, current and stored charge.
4. Battery tests above a declared cell energy run only in a rated containment chamber with gas detection.

KLN-O-HW-1 seeds limit violations and a missing assessment.

### R10-08 · Major · Targets: MFG, KLN, AGT, CONTRACT
**Section:** MFG "Approval, transfer and physical safety" (`ProgramSubject`); KLN D-KLN-38; AGT D-AGT-20
**Problem:** The program subject signs data that shops change every shift.
- `machine` names one machine, so moving a job to an identical sister machine needs a new program approval.
- `tool_table` maps tools to pockets, which random-access tool changers reassign while running.

On top of that, every transfer needs its own WebAuthn Approval by an assigned approver. Approvals are single-use, standing pre-approvals are rejected, and a session may hold three pending requests, so a cell programmer feeding six machines is throttled. Shops will route around this.
**Evidence:** MFG: "`ProgramSubject { programs, machine, controller, tool_table, setup_sheet, verdicts, block_map }`"; "Per-machine tool tables | Tool Assemblies → T number, pocket, H and D registers". AGT D-AGT-20: "Rejected: ... standing pre-approvals". Contract 7.6: "At most three pending requests per session".
**Fix:**
1. The subject binds the machine class and nominal tool assemblies by T number, never a serial or a pocket. The class is the machine package version, controller family and software version, and post version. MFG-O-POST-3's qualification record lists the serials qualified for the class.
2. Instance data (pockets, measured lengths and radii, work offsets, calibration) stay outside the subject. The gateway verifies them at transfer against the setup sheet's tolerances.
3. A `Released` program may go to any qualified serial of its class through R10-02's pull path, on an operator's request at that machine. The program's release Approval serves as the plan's approval. Remote pushes keep the assigned Approval.
4. Contract 7.6 states this one exception to D-AGT-20 explicitly.

### R10-09 · Major · Targets: MFG
**Section:** MFG D-MFG-24; capability row "Pre-run offset verification"
**Problem:** The check is named pre-run but runs before transfer. Operators routinely touch off tools and set work offsets after loading a program and before cycle start. The offsets that decide a crash are therefore set after the gateway's check, so a pass at transfer says little about the run. R4-05's fix does not hold here.
**Evidence:** D-MFG-24: "It reads tool and work offsets and re-simulates with them before transfer". Row: "Pre-run offset verification | Offsets read; collision re-simulated with actual gauge lengths".
**Fix:**
1. Rename the row "Transfer-time offset verification".
2. Add an "Offset watch" row. From transfer until the program ends, the gateway re-runs the gouge and collision checks on every change to a referenced H, D or work-offset register. This works wherever the connector reads offsets: vendor connectors in phase 2, MTConnect `ToolOffsets` and `WorkOffsets` in phase 3.
3. On a change that fails, the gateway raises a machine-side alarm and an andon event within 5 s (target), naming the register and the predicted collision. It cannot block the cycle, and the setup sheet says so.
4. The setup sheet prints the verified values with their tolerances for the operator's check before cycle start.

MFG-O-SAFE-4 adds offset edits made after transfer.

### R10-10 · Major · Targets: MFG
**Section:** MFG D-MFG-24 (header hash); `Controller.files`
**Problem:** Controls rewrite programs they store. They change line endings and case, strip or reformat comments, add or drop block numbers and leading zeros, and normalize the program-number line. A hash over posted bytes then fails on read-back of correct programs, and users learn to ignore `HashMismatch`. The header line also cannot include its own hash, and long header comments exceed some controls' comment limits.
**Evidence:** D-MFG-24: "Posts write item, revision, release id and a short content hash into the program header, and the gateway recomputes the hash on transfer and on read-back." `FileRules` describes only writing ("line endings, character set, length, size, names").
**Fix:**
1. Define the hash over the canonical token stream of the semantic NC parser that already powers the semantic NC diff (MFG-O-POST-4). It is computed per dialect and excludes the header line.
2. `FileRules` declares each control's storage normalizations.
3. The header comment carries item, revision and 12 hexadecimal digits of the hash, within the control's comment limit.
4. A mismatch reports the semantic NC diff, not two hashes.

MFG-O-SAFE-2 adds round trips through each family's simulator and the reference shop's controls: correct programs never mismatch, and seeded single-token edits always do.

### R10-11 · Major · Targets: MFG, AGT
**Section:** MFG "Approval, transfer and physical safety"; `Controller.files`
**Problem:** Controls address programs by number or short name. Storing a program under a number already in memory overwrites the old one or is rejected, depending on the control. MFG says nothing about:
- how a program Item maps to a number or name per machine;
- how subprograms called by the main program travel with it;
- what happens when the number is taken.

Overwriting another job's program is a classic way to run the wrong program.
**Evidence:** MFG's Act table and D-MFG-24 cover header and hash only. No capability row allocates program numbers, and `FileRules` mentions only "names".
**Fix:**
1. Add a per-machine program registry to the gateway. Each program Item gets a stable number or name per machine class, kept across revisions. Subprograms belong to the transfer set.
2. Before transfer the gateway reads the control's directory. It refuses to overwrite a program Crucible did not store, with `ProgramSlotOccupied { number, foreign: true }`, and overwrites a Crucible program only with a later revision of the same Item.
3. The setup sheet prints the number, and the approval page states what is replaced, for example "replaces O1234, bracket rev B".

New oracle MFG-O-SAFE-6: seeded collisions are refused in 100% of cases.

### R10-12 · Major · Targets: MFG
**Section:** MFG "Machines, controllers and posts"; "Machining simulation and NC verification"; DNC row
**Problem:** After a broken tool, a power loss or a drip-feed fault, operators restart mid-program by block search. A restart that skips the tool call, length offset, work offset or spindle start is one of the commonest crash causes. Crucible simulates only full runs from the first block, and the DNC row says a fault is "never resumed automatically" without giving a safe way to resume.
**Evidence:** MFG has no restart, block-search or sequence-number capability. DNC row: "A fault stops the feed; never resumed automatically".
**Fix:**
1. Posts emit a restart point at every workingstep and tool change: a sequence number followed by a full modal restatement. The restatement covers the tool call, length offset, work offset, plane, units, absolute mode, spindle, coolant and an approach from the clearance plane.
2. Simulation verifies each restart entry from the tool-change position.
3. The setup sheet lists the restart points. A restart inside a workingstep is `Unsupported`.
4. Drip feed resumes only from a restart point, on a request made at the control (R10-02).

New oracle row: every restart entry simulates collision-free, and seeded restarts that skip the restatement are caught.

### R10-13 · Major · Targets: MFG, UIX
**Section:** MFG "Scope, layering and core types" (`Toolpath`, `Workingstep`); `MotionSemantics.cutter_comp`; posts
**Problem:** Shops hold tight wall and bore sizes by letting the operator adjust a wear offset at the control. That needs posts to output control-side or wear-mode cutter compensation (G41 and G42 with a D register). MFG's types have no compensation mode, so the gouge check cannot know that a finishing pass moves with a value set later at the control.
**Evidence:** The `Toolpath` and `Workingstep` records have no compensation field. `MotionSemantics` declares only "cutter_comp: look-ahead blocks, entry rule".
**Fix:**
1. Add `comp: CompMode { Computer, Control, Wear, ReverseWear }` and `wear_range: Range<Length>` to finishing workingsteps, defaulting to `Computer`.
2. Posts emit G41 or G42 with the D register for the other modes.
3. Gouge and collision checks run at both ends of the declared range.
4. The gateway's offset check verifies that the D register lies inside the range, and the setup sheet prints it.

MFG-O-SIM-1 seeds wear values outside the range. UIX's NC panel shows the mode per workingstep.

### R10-14 · Major · Targets: MFG, ECO
**Section:** MFG D-MFG-28 (`verify_nc`); "Milling, drilling and probing strategies" (probing paths)
**Problem:** D-MFG-28 promises to verify "any NC text", but `verify_nc` cannot simulate two common patterns. Programs from other CAM systems and from hand programming:
- call macros stored in the control (builder tool-change macros, probe makers' cycles, custom G- and M-code macros), whose source `verify_nc` lacks;
- branch on system variables that read live state (current position, probe results, tool-life counters), whose outcome is a measurement.

Many also write offsets from inside the program. MFG's own on-machine probing emits the same kind of calls.
**Evidence:** D-MFG-28: "A product NC interpreter ... verifies any NC text, including programs from other CAM systems and hand programming". The capability table lists "Macro B variables", "R parameters, GUD variables" and "Q parameters".
**Fix:**
1. The machine package carries a macro library captured from the control or the macro's maker, under its licence. A call to a macro not in the library is `Unsupported { macro }`; its motion is bounded by a declared envelope, or verification fails.
2. System variables that read live state are typed inputs with declared ranges. `verify_nc` explores both outcomes of each branch they control, up to a declared branch budget, then returns `Undecided`.
3. Programs that write offsets are flagged, since they change values the gateway checked.

MFG-O-SIM-3 adds macro-calling and probe-branching programs with planted crashes.

### R10-15 · Major · Targets: MFG, KLN
**Section:** MFG D-MFG-28; "Change impact" row; KLN D-KLN-38
**Problem:** Imported legacy NC programs are program Items "never converted to workingsteps", so they have no targets. The change-impact rule selects "exactly the programs whose targets or setups changed", so it never selects them. When the part changes, a legacy program stays `Released` and transfers without re-verification.
**Evidence:** D-MFG-28; change-impact row ("A design change invalidates exactly the programs whose targets or setups changed"). KLN: "An engineering order that changes a part returns exactly its dependent programs to `Prototype`."
**Fix:** A legacy program Item declares `verified_against: [ItemRevision]` for the parts and fixtures it was verified with.
1. A change order revising any of them returns the program to `Prototype`, as for generated programs.
2. `verify_nc` re-runs against the new revision and reports the regions where simulated stock and the new design differ.

MFG-O-SAFE-1 adds a legacy program on a revised part.

### R10-16 · Major · Targets: KLN, MFG
**Section:** KLN D-KLN-38; MFG "Quality records: SPC, MSA, FAI and PPAP"
**Problem:** Program Items ship with CAM in phase 2. They become `Proven` "after a passing first-article record", then `Released`. AS9102 first-article reports and QIF results as Evidence records arrive only in phase 3, and nothing in phase 2 defines a first-article record. GP3 and GP4 programs therefore cannot leave `Prototype`.
**Evidence:** KLN D-KLN-38: "`Proven` (after a passing first-article record)". MFG: "AS9102 and partial FAI ... 3"; "Results as Evidence records ... 3".
**Fix:**
1. KLN and MFG define a first-article record as a signed record joining the program revision, machine serial, part serial and one passing Evidence record per characteristic. It is built on R10-03's phase 1 loop.
2. AS9102 forms in phase 3 render the same record.
3. MFG adds a phase 2 row "First-article record", checked by MFG-O-QUAL-2's partial-scope cases.

### R10-17 · Major · Targets: CONTRACT, AGT, UIX, MFG
**Section:** Contract 7.6 Act approvals; AGT "Acts and approvals" (approval page); UIX D-UIX-29
**Problem:** The one approval page shows file names, a thumbnail, a content summary (Items, labels, bytes), recipient verification and screening dates, and a diff. Those fit data release. For a physical-effect plan the approver sees nothing that bears on safety:
- which device it is, and where;
- what the transfer overwrites;
- the simulation verdicts and minimum clearance;
- the gateway's offset result;
- what the person at the device must do.

MFG's rule that robot programs are "Proved in manual reduced-speed mode" appears nowhere a person reads it.
**Evidence:** Contract 7.6 lists the page contents. MFG: "`send_robot_program` | Delivers a robot program | Proved in manual reduced-speed mode; never writes safety configuration".
**Fix:** Contract 7.6 adds a physical-effect section to the page:
- device serial, location and controller version;
- program number and what it replaces (R10-11);
- simulation verdicts, with the minimum clearance and the count of `Unsupported` semantics;
- gateway offset results with their timestamp;
- the setup-sheet revision;
- the required on-device steps, each shown as an instruction to the person at the device: reduced-speed prove-out, tool-length check, reduced override, propellers off.

AGT-O-9 adds rendering cases for each physical-effect class.

### R10-18 · Major · Targets: MEC, MFG, COV
**Section:** MEC "Lattices and machine elements"; MFG "Turning, EDM, gears and grinding"; COV model levels
**Problem:** GP3 is a gearbox in phase 2, but no tab specifies gear load capacity or accuracy. MEC covers geometry to ISO 21771-1 only. MFG says "MEC owns gear geometry and rating", and its oracle reads "the design's quality grade", which no MEC record holds. COV mentions "gear rating" only as an example of an L0 model. A practitioner rates every gear for pitting, bending and scuffing, puts the accuracy grade and inspection data in a gear data table on the drawing, and checks bearing life.
**Evidence:** MEC machine-element table: "Involute spur and helical gears | ... | ISO 21771-1:2024". MFG: "MEC owns gear geometry and rating". MFG-O-GEAR-1: "Simulated flanks within the design's quality grade". COV L0 row: "gear rating".
**Fix:** Add the following in phase 2, with oracles from the standards' worked examples:
1. MEC's gear record gains an accuracy grade to ISO 1328-1 [unverified edition].
2. A rating check library implements ISO 6336 parts 1, 2, 3 and 6, or ANSI/AGMA 2101 [unverified editions], as L0 models with COV envelopes and margin Fields.
3. Catalog bearings get ISO 281 rating life [unverified edition] from the gear record's load spectrum.
4. Drawings gain a gear data table: module, teeth, pressure and helix angles, profile shift, modifications, grade, and span or over-pins measurement.

### R10-19 · Major · Targets: MFG, MEC
**Section:** MFG "Turning, EDM, gears and grinding" (gear generating); MFG Phasing, phase 2
**Problem:** Phase 2 promises hobbing, shaping and power skiving "through machine cycles", but gear machines are programmed through the builders' gear software, as parameter sets rather than ISO 6983 programs. Power skiving also needs synchronized multi-axis motion that phase 2's 3+2 collision check does not cover. The stated fix for an unsupported machine, 5-axis gear milling, is phase 3. GP3 needs neither capability if the shop cuts its gears.
**Evidence:** MFG: "Gear generating | Hobbing, shaping and power skiving from MEC's gear record through machine cycles | `Unsupported`; fix: 5-axis gear milling | MFG-O-GEAR-1 | 2"; "5-axis gear milling ... 3"; "Machine collision ... 2 (to 3+2), 3 (5-axis)".
**Fix:**
1. Phase 2 gear output is the gear data table and inspection plan (R10-18) for the shop's own gear process. Crucible programs cut GP3's housings, shafts and blanks.
2. Gear generating moves to phase 4. Before it ships, MFG names for each machine family whether output is ISO cycle calls or a parameter set for the builder's software.
3. Power skiving waits for simultaneous 5-axis collision checking.

### R10-20 · Major · Targets: MFG, MEC, ECO
**Section:** MFG "Sheet cutting, nesting and press brake"
**Problem:** GP4 needs press-brake planning and profile cutting in phase 2, but neither has an output a machine reads. Posts cover four milling and turning families. No press-brake control, laser, plasma or waterjet controller is named, and press brakes are usually programmed in the builder's offline software or at the control. A bend plan without an output becomes a paper note.
**Evidence:** MFG rows "Press-brake planning | Bend sequence, tool stations and backgauge" and "Profile cutting and ordering", both phase 2. Posts: "Fanuc, Haas, Siemens and Heidenhain".
**Fix:**
1. Press brakes, phase 2: a bend sheet generated as an Ingot drawing (sequence, punch and die ids and stations, backgauge positions, target angles, flange lengths, the flat pattern with bend lines), plus a STEP of the bent part and the flat DXF, which brake offline software imports.
2. Profile cutting, phase 2: a generic ISO 6983 cutting post whose pierce, lead-in and process codes are `Controller` data, plus the DXF hand-off for the cutter's own CAM.
3. Native press-brake programs arrive in phase 3 through `send_to_machine` (R10-04), for families named after a survey of the reference shop.

### R10-21 · Major · Targets: MEC, MFG, ING
**Section:** MEC "Tolerancing" (stack-up, completeness); MEC "Drawings" (general-tolerance tables)
**Problem:** Most dimensions on a real part carry no explicit tolerance. A general tolerance governs them: ISO 2768-1 classes, an ISO 22081 general specification, or an ASME title-block rule. In Crucible an untoleranced length is exact. A worst-case stack counts it as zero, MFG extracts no characteristic for it, cost ignores it, and inspection has no limit for it. The general tolerance exists only as a drawing table.
**Evidence:** MEC: "Size tolerances are `Tol<T>` values"; "Worst case | Affine `Tol` sum over a closed, signed contributor chain"; drawing row "hole and general-tolerance tables".
**Fix:**
1. Add `general_tolerance(standard, class)` to `std::mech::tol` as a Part-level record (ISO 2768-1 class, ISO 22081 general specification, or ASME decimal-place rules) that the drawing renders.
2. Stacks, characteristic extraction, inspection plans, tolerance-driven cost and KLN's definition tolerance read it for every untoleranced size, location and angle. Reports label those contributors "general".
3. Ingot arithmetic is unchanged: the record applies at the tolerancing layer.
4. A Part without a general tolerance fails `check::standards` before release.

### R10-22 · Major · Targets: MFG, ECO, CONTRACT
**Section:** MFG "Additive processes and build preparation" (category table); MFG Phasing, phase 2; contract 13.1, phase 2
**Problem:** The phase 2 gate needs "one additive part printed through Crucible's slicer" without naming a process. MFG's phase 2 powder-bed output is "own scan vectors in 3MF Toolpath", an extension MFG itself calls "still a draft", and no tab names a machine or build processor that reads it. If the gate part is metal PBF, the gate depends on a format nobody consumes.
**Evidence:** MFG: "Powder bed fusion ... own scan vectors in 3MF Toolpath (2)"; "the Toolpath extension was updated on 17 September 2026 and is still a draft".
**Fix:**
1. Contract 13.1 names the phase 2 slicer part as material extrusion on an open-firmware printer (Klipper or RepRapFirmware), sent through `send_print_job`.
2. PBF scan vectors move to the phase in which a named machine partner accepts 3MF Toolpath or another open vector format, recorded with contract 13.2's partner agreements.
3. Metal PBF compensation (MFG-O-AM-8) stays a geometry change sent through the vendor's build processor.

### R10-23 · Major · Targets: MFG, ECO, CONTRACT
**Section:** MFG D-MFG-11, D-MFG-25 and "Slicer hand-off"; contract 13.1 (GP2) and 13.2 (phase 0 agreements)
**Problem:** GP2 is a lattice part printed in phase 1 "with the printer vendor's slicer" from Crucible's 3MF. Nothing states whether that build processor reads the 3MF Beam Lattice extension, and MFG-O-AM-2 names only three FFF slicers. A dense lattice triangulated for a processor that does not read it is the bottleneck D-MFG-11 cites. For example, a 100 mm part with 2 mm cells has about 1.25 × 10⁵ cells. At about 10³ triangles per cell for a 10 µm chordal error, that is of the order of 10⁸ triangles (estimate).
**Evidence:** D-MFG-11: "triangulating a dense lattice is the bottleneck of conventional build preparation". MFG-O-AM-2: "Each named slicer opens the 3MF with plates, orientation and settings intact". ECO's phase 1 3MF scope is Core, Production, Materials and Beam Lattice.
**Fix:**
1. The phase 0 print-bureau agreement includes a file-acceptance test of the bureau's build processor on three files: a 3MF with Beam Lattice, a 3MF of Core triangles at a stated chordal error, and a sliced build where the processor takes one.
2. MFG-O-AM-2 extends to that build processor.
3. MFG states a mesh-export target for GP2 (triangle count, chordal error and file size, labelled as targets), and the GP2 lattice density is chosen within it.

### R10-24 · Major · Targets: ELX, KLN
**Section:** ELX D-ELX-3 and D-ELX-5 (catalog selections and offers)
**Problem:** A `CatalogSelection` re-resolves whenever its arguments change. It may rank by price or stock from pinned offers, and `crucible update parts` refreshes those offers. After layout and release, a part choice is a qualified decision. A price refresh or an upstream edit can still swap the manufacturer part number, or the land pattern, of a placed part, and the next build's assembly BOM changes without a change order. A diff that lists substitutions is not the control component engineering expects.
**Evidence:** D-ELX-3: "A selection re-resolves whenever its arguments change; `crucible update parts` refreshes only the data pins, and its diff lists every substitution."
**Fix:**
1. When a board's layout is first released or locked, each selection records its resolved part in the BOM data module (`resolved: parts::…`).
2. After that, re-resolution never changes the part. It opens a Proposal ("selection now prefers X", with the reason), and a re-pick that changes the land pattern fails with `SelectionChangesLandPattern`.
3. Price- and stock-ranked picks never change a released board's assembly BOM outside a change order.

ELX-O-CAT-3 adds a post-release offer refresh that must leave the BOM unchanged.

### R10-25 · Major · Targets: ELX, MFG
**Section:** ELX "Design rules and the constraint manager" (D-ELX-24)
**Problem:** Spacing comes either from fabricator minimums or from an isolation barrier declared under a safety standard. Most boards also carry functional voltages (24 V, 48 V and 100 V buses) that cross no safety barrier but still need voltage-dependent spacing. Board designers take it from IPC-2221's conductor-spacing table, which separates internal layers, uncoated and coated external layers, and altitude. Without it they hand-write rules. Conformal coating changes those values and needs keep-outs over connectors and test points, yet has no record either.
**Evidence:** ELX's rule example uses only `fab.min_space` and `iso.creepage()`. Neither ELX nor MFG refers to IPC-2221 or coating.
**Fix:** Both arrive in phase 3 with DRC.
1. Add `functional_spacing(nets, voltage)` to `std::electronics::rules`. It reads a licensed IPC-2221 data package [unverified edition] with columns for internal, external uncoated by altitude, external coated, and assembly. Voltages come from `Power` ranges and net classes.
2. Add a `conformal_coating` board record (material, thickness, keep-out regions). It selects the coated column, feeds MFG's assembly package, and fails test-point access checks under coating.

### R10-26 · Major · Targets: CONTRACT, ECO, KLN, AGT
**Section:** ECO D-ECO-28 and D-ECO-30; KLN D-KLN-39; contract 2 (Act) and 7.6
**Problem:** Every outbound enterprise-connector message is a `release_data` Act, and every Act commits only after an assigned human WebAuthn Approval of its digest. A release normally triggers item-master, BOM and change-notice messages to the ERP and MES. As specified each needs its own approval, so approvers either rubber-stamp a stream of sync messages or the ERP drifts. KLN folds publication into an external PLM into the release Act; ERP and MES messages get no such treatment.
**Evidence:** D-ECO-28 lists "enterprise-connector messages" among the Acts. D-ECO-30: "Outbound messages are `release_data` Acts." Contract 2: "`act.commit` runs only after an assigned human Approval of that digest."
**Fix:**
1. Contract 7.6 adds: "An Act plan may carry several effects, and one Approval covers them."
2. Release, change-notice and deviation plans list their deliveries to recipients marked `internal_system` (ERP, MES, enterprise PLM), whose recipient records are verified under the two-person rule. The release Approval covers them.
3. Failed deliveries retry under the same approval until the plan expires.
4. Messages outside a release, such as a new-part request into the ERP, remain separate Acts.

ECO-O-27 adds a release whose plan carries ERP and MES effects.

### R10-27 · Major · Targets: MFG
**Section:** MFG Oracles
**Problem:** Several MFG oracles have no machine-checkable pass criterion:
- MFG-O-MOLD-4 names "a published plaque benchmark [unverified which]".
- MFG-O-FORM-2 and MFG-O-JOIN-2 cite published benchmarks marked [unverified], and MFG-O-BULK-1 cites "published die-fill and load benchmarks".
- MFG-O-TOOL-2 ("Predicted changes against as-run records") and MFG-O-FEED-2 ("Predicted power matches measured") state no tolerance.
- MFG-O-AM-7 and MFG-O-TREAT-2 measure "where data exist" or "on golden parts" without a bound.
- MFG-O-NEST-1 targets sparrow's density "at equal work", but sparrow's published runs are wall-clock limited, so "equal work" is undefined.
**Evidence:** The oracle rows quoted above. Sparrow's README sets a global time limit, 600 s by default (https://github.com/JeroenGar/sparrow).
**Fix:** Give each oracle a dataset and a number:
- springback on named NUMISHEET benchmark cases [unverified edition], within a stated angle;
- weld residual stress on the NeT TG1 single-bead plate [unverified], within a stated MPa band;
- fibre orientation on Bay and Tucker's centre-gated disk data [unverified], within a stated error in the orientation tensor component a₁₁;
- AM-Bench bridge-structure deflection within 10% (target);
- tool-life prediction within ±25% of as-run counts (target);
- spindle power within 10% of spindle-load data (target);
- nesting density within one point of sparrow at equal wall-clock time on the reference laptop, with the work-unit budget calibrated to that time.

Loosening any tolerance needs human approval, as ELX's oracles already state.

### R10-28 · Major · Targets: MFG, PLT, CONTRACT
**Section:** MFG Open questions 12; D-MFG-20 and D-MFG-24; contract 12
**Problem:** The gateway carries most of the shop-floor safety logic: hash and read-back, offset checks, edit capture and DNC, plus R10-01's egress filter, R10-02's pull path and R10-11's registry. Yet no crate, platform, packaging or network posture is specified. Shop DNC computers often run Windows, many lack a TPM, and an OT network must not accept inbound connections from the office network.
**Evidence:** MFG OQ12: "Contract 12's crate map lists no gateway app under `apps/`". MFG: "Gateway | Shop-network gateway for machines, printers and CMMs; device key under measured boot; offline buffering".
**Fix:** Answer to MFG OQ12.
1. Contract 12 adds `apps/gateway`, owned by MFG and packaged by PLT for Linux x86-64 and ARM64 and Windows 11 x86-64.
2. The gateway connects outbound only, as KLN's runners do, so the factory network needs no inbound ports. It runs connectors out of process (contract 7.4) behind its own wire-level egress filter.
3. Signing External inputs requires TPM 2.0. A gateway without one may transfer programs, but its readings carry `data_untrusted` and cannot serve `SignOff` checks.
4. The safety functions (no start, pull-only DNC, the registry) live in the gateway's core, never in connectors, so a connector update cannot change them.
5. Network guidance cites IEC 62443-3-3 zones and conduits [unverified edition].

### R10-29 · Major · Targets: MFG
**Section:** MFG Open questions 2; MFG-O-POST-1; MFG-O-SIM-2
**Problem:** Post qualification and the crash corpus need each control family's real interpolation of rapids, rotary unwinding and reference returns. MFG asks whether physical controls or licensed virtual controllers should provide it. A crash corpus cannot run on a machine with axes enabled, and virtual controllers do not exist for every family.
**Evidence:** MFG OQ2. MFG: "A family's post ships only after zero false negatives on the controller-semantics crash corpus."
**Fix:** Answer to MFG OQ2.
1. Capture on the reference shop's physical controls, in each family's program-test mode (machine lock or dry-run graphics), in which the control interpolates and reports positions while axes stay still [unverified mode names per family].
2. Sample commanded positions through the vendor connector or MTConnect. Licensed vendor programming stations serve only as a second source.
3. A family's post ships when the captured traces of the whole crash corpus match the simulator's `MotionSemantics` within the declared tolerance.
4. The reference-shop agreement in contract 13.2 adds controller-capture time.

### R10-30 · Major · Targets: KLN, MEC
**Section:** KLN Open questions 3; KLN merge condition 5
**Problem:** The geometric provenance condition flags a new entity that touches the other side's modified region "at or below the merge clearance (default 0 mm)". Welded members, mated faces and press fits in GP4 would then conflict on every merge that touches them, and GP4 work would serialize.
**Evidence:** KLN condition 5 and KLN OQ3: "Welded members in GP4 touch by design, so a 0 mm merge clearance flags them".
**Fix:** Answer to KLN OQ3. Reuse MEC's interference classes. A contact explained by a mate, a `Weld` record, a fastened joint or an `IntendedFit` is exempt from condition 5, as it is from interference errors, and only unexplained contact conflicts. KLN-O-MERGE-1 adds GP4 branches that edit adjacent welded members.

### R10-31 · Minor · Targets: MFG, AGT
**Section:** MFG D-MFG-20; "No motion commands" row; MFG-O-SAFE-3
**Problem:** The OPC UA rule is a denylist. ISA-95 Job Control defines eleven methods. MFG forbids `Start`, `StoreAndStart`, `Resume` and `RevokeStart` but says nothing of `Update`, `Pause`, `Stop` or `Abort`, while `RevokeStart` only withdraws permission and is harmless. A connector author can read the gap as permission to call `Update` on a running job.
**Evidence:** OPC 10031-4 section 6.3 lists Store, StoreAndStart, Start, RevokeStart, Pause, Resume, Update, Abort, Stop, Cancel and Clear (https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3).
**Fix:** State an allowlist everywhere. Crucible calls `Store` only inside `store_machine_job`, and `Cancel`, `Clear` and `RevokeStart` only on jobs it stored that have not started. Every other method is uncallable. MFG-O-SAFE-3 checks the allowlist, together with R10-01's wire criterion.

### R10-32 · Minor · Targets: MFG, KLN
**Section:** MFG D-MFG-24 (edit capture); KLN "Change orders" (Deviation)
**Problem:** MFG says parts made from a program edited at the control "get an as-built deviation". In KLN, though, a deviation is a pre-approved, time-limited departure granted by the `grant_deviation` Act. A part made from an unapproved program is a nonconformance awaiting disposition, so one word names two concepts.
**Evidence:** MFG: "parts made from it get an as-built deviation". KLN: "Deviation | A temporary departure for given serials or lots, with expiry; granted by the `grant_deviation` Act".
**Fix:** MFG writes "a nonconformance record, linked to the serials, for disposition" (its "Nonconformance" capability), and "deviation" keeps KLN's meaning.

### R10-33 · Minor · Targets: MFG, ECO
**Section:** MFG "Factory connection and digital twin" (MES and ERP mapping); ECO "Enterprise connectors"
**Problem:** ECO ships ERP and MES connectors in phase 2 and says Crucible owns MBOM and routings where it plans manufacturing. MFG ships MBOM and routings in phase 2 but maps routings and work orders through the connectors only in phase 4. Phase 2 MES connectors therefore carry no routing data.
**Evidence:** ECO: "ERP and MES connectors | Mapped records out; External inputs in; field ownership | ... | 2". MFG: "MES and ERP mapping | Work orders, routing status, scrap and labor ... | 4"; "MBOM and routings ... | 2, 3".
**Fix:** MFG moves the outbound routing and work-order mapping to phase 2, with its MBOM and routings. Scrap, labor and status feedback may stay in phase 4.

### R10-34 · Minor · Targets: MFG, ELX
**Section:** MFG "Electronics and harness manufacturing handoff"; ELX D-ELX-23; ELX "Pours, planes and vias"
**Problem:** Three gaps remain in the board-house vocabulary:
- MFG's fabrication package omits the IPC-D-356 netlist, which ECO writes and many fabricators use for bare-board test of Gerber packages.
- Vias have no IPC-4761 protection type (tented, plugged, filled, capped), which via-in-pad needs on the fabrication drawing.
- Classes start at 2, though Class 1 governs much consumer work.
**Evidence:** MFG's package list: "IPC-2581C, Gerber X2, XNC drill and route, Gerber job file, impedance and stackup tables, or ODB++". ECO: "Gerber, XNC, IPC-2581C, ODB++, IPC-D-356, placements". ELX: "Class 2, 3 or 3/A".
**Fix:**
1. Add IPC-D-356 to the Gerber package list.
2. Add `protection: Ipc4761Type` per via class, with a fabrication-drawing note and a DFM rule for via-in-pad [unverified edition].
3. Accept Class 1 in `fab_class` and `assembly_class`.

### R10-35 · Minor · Targets: MFG
**Section:** MFG "Additive processes and build preparation" (Bambu); Open questions 9
**Problem:** MFG says "Crucible reaches Bambu printers only through that path" (Bambu Connect). Bambu later added an optional LAN Developer Mode that leaves MQTT, the live stream and FTP open, without vendor support, so the claim is out of date.
**Evidence:** Developer Mode lets users "leave the MQTT channel, live stream, and FTP open", and Bambu "will not be able to provide customer support for this mode" (https://blog.bambulab.com/updates-and-third-party-integration-with-bambu-connect/).
**Fix:** Answer to MFG OQ9. Support two paths and replace "only through that path":
1. On printers the owner sets to Developer Mode, `send_print_job` uploads over FTP only and never sends an MQTT print command. The site policy records that the owner accepted an unsupported mode.
2. Otherwise the desktop client hands the job to Bambu Connect, where a person starts it.

### R10-36 · Minor · Targets: MEC
**Section:** MEC Open questions 6 and 7
**Problem:** Two open questions on drawings and dialects block the drawing editor's design.
**Evidence:** MEC OQ6: "Should editing a driving dimension on a drawing write model source through its `Query`?" MEC OQ7: "Is a Proposal-based ASME-to-ISO translation worth building?"
**Fix:**
- OQ6: Yes. Editing a driving dimension on a drawing is an `api` Edit on the `dim` or feature parameter its `Query` resolves to, shown as a source diff. Reference and driven dimensions refuse with the reason. Users expect this from mid-range CAD tools, and under principle 2 the drawing is one more view of the program, not a separate geometry editor.
- OQ7: In phase 2, build only a non-equivalence report: the controls with no exact counterpart, each with the clause behind it. A translating Proposal waits for customer demand, because partial automatic translation invites parts made to the wrong requirement.

### R10-37 · Minor · Targets: MEC, MFG
**Section:** MEC Open questions 3
**Problem:** MEC asks which processes accept a released part with an implicit blend region. The answer decides a release check.
**Evidence:** MEC OQ3: "Which processes accept a released part with an implicit region? Proposal: MFG process rules decide".
**Fix:**
1. Only processes that consume implicit or mesh geometry accept implicit regions: additive through 3MF.
2. Any process whose hand-off is STEP (machining, molding, sheet) requires conversion to B-rep before release, with the deviation inside the face's tolerance or general tolerance (R10-21).
3. MFG's process rule checks this, and `check::standards` enforces it.

Shops' CAM and CMM software read B-rep, not implicit fields.

### R10-38 · Minor · Targets: MEC
**Section:** MEC "Revisions, balloons and generated drawings" ("PDF/A [unverified: ISO 19005 part]"); Open questions 9 (R4-16)
**Problem:** The PDF/A part for release drawings is still open, and archive validation needs it fixed.
**Evidence:** ISO 19005-2:2011 is "Use of ISO 32000-1 (PDF/A-2)" (https://www.evs.ee/en/iso-19005-2-2011). ISO 19005-4:2020 is "Use of ISO 32000-2 (PDF/A-4)" (https://www.evs.ee/en/iso-19005-4-2020).
**Fix:**
1. Write release drawings as PDF/A-2, conformance level u. It builds on ISO 32000-1, which current PDF viewers and validators read.
2. Offer PDF/A-4 as an option.
3. Pin the choice in the drafting package so a move is an explicit update.

### R10-39 · Minor · Targets: KLN, MEC
**Section:** KLN Open questions 8 (definition tolerance)
**Problem:** A fixed default can sit below what a large Body's scale-relative resolution resolves. An engine upgrade would then mark every large released Item modified, the noise D-KLN-26 exists to remove.
**Evidence:** KLN OQ8: "MEC should confirm the default of the smaller of 0.1 µm and 1% of the tightest tolerance". Contract 7.1: "Per-Body scale-relative resolution".
**Fix:** Keep the smaller of 0.1 µm and 1% of the Item's tightest tolerance, with two amendments:
1. Use the general tolerance (R10-21) when nothing tighter exists.
2. Never go below ten times the Body's resolution.

### R10-40 · Minor · Targets: MFG
**Section:** MFG Open questions 3, 7 and 8
**Problem:** Three open questions on anytime budgets, the COV–MFG data boundary and stock representation have no proposed answers.
**Evidence:** MFG OQ3 ("run for 10 minutes"), OQ7 ("Where does COV's material model ownership end"), OQ8 ("A benchmark run before phase 2 decides").
**Fix:**
- OQ3: Keep fixed work budgets per evaluation class, shown as an estimated time on the reference laptop. Offer "continue", which warm-starts from the best result with a larger budget; warm starts never worsen a result (MFG-O-NEST-1).
- OQ7: COV owns material state models and their envelopes: Cross-WLF, Tait pVT, solidification paths and fraction-solid curves. MFG owns process parameters, machine and mould data, coupon programs and calibration records. A coefficient fitted from a process coupon lives in MFG's process profile and cites COV's model id.
- OQ8: Benchmark GP3's programs at each setup's stated stock tolerance. Choose tri-dexel only if it meets the tolerance with no more memory than the grid and within PLT's heavy-worker cap.

### R10-41 · Minor · Targets: MEC
**Section:** MEC "Sheet metal" (bend-rule defaults)
**Problem:** The constant default K factors (0.45 for bends, 0.5 for rolled walls) misstate flat lengths for tight bends, where the neutral fibre moves inward as the inside radius approaches the thickness. A new shop without bend tables uses the default on every bend.
**Evidence:** MEC: "Onshape's documented K factors (0.45 for bends, 0.5 for rolled walls) are defaults until a table overrides them."
**Fix:**
1. Default `KFactor` from a relation that depends on the ratio of inside radius to thickness (DIN 6935's correction factor [unverified]), keeping the constant only as a fallback.
2. Print the K factor used for each bend in the bend table.

### R10-42 · Minor · Targets: MEC, MFG
**Section:** MEC "Weldments and structural frames"; MFG "Welding, joining and composites"
**Problem:** In Europe, welded structural steel is made to EN 1090-2 execution classes. The class sets the ISO 5817 level, the NDT extent and the ISO 3834 quality requirements. GP8's platform needs one, as do many frames like GP4's, but neither tab records it.
**Evidence:** MEC's `Weld` record carries "the imperfection quality level: ISO 5817 level B, C or D, or AWS D1.1 acceptance criteria", with no execution class. MFG lists procedure standards only.
**Fix:**
1. Add `execution_class: Exc1..Exc4` (EN 1090-2 [unverified edition]) to weldment Parts.
2. MFG derives default quality levels, NDT extent and the required ISO 3834 part from it.
3. Phase 2 records the class, and phase 5 enforces it for GP8.

### R10-43 · Minor · Targets: MFG
**Section:** MFG "Assembly and work instructions" (robot programming)
**Problem:** The robot post list hides how each program reaches its controller. FANUC TP programs are binary on the controller; a post can produce only the text form, which needs a paid ASCII-upload option or the vendor's offline converter [unverified]. Other families have their own loading conventions.
**Evidence:** MFG: "posts to RAPID, KRL, FANUC TP, INFORM and URScript [unverified] without safety configuration".
**Fix:**
1. For each robot family, the machine package states the output file type and its loading path.
2. A post fails with `Unsupported { capability: AsciiUpload }` when the controller lacks the option it needs.
3. R10-01 applies to every family's loading path.

### R10-44 · Minor · Targets: KLN
**Section:** KLN Open questions 4 and 5
**Problem:** Revision-label rules and the home of item numbers are open, and D-KLN-39's external system of record makes the second one urgent.
**Evidence:** KLN OQ4: "Revision letters and markers need confirmation against ASME Y14.35-2025". KLN OQ5: "Keep them in Ingot ... or only in records keyed by lineage?"
**Fix:**
- OQ4: A policy package pins revision rules and cites ASME Y14.35-2025, the current edition. By default it excludes the letters I, O, Q, S, X and Z [unverified against the standard text], and customers may override it.
- OQ5: Keep item numbers in records keyed by lineage, and reference them from source by a local key (`item: key("bracket")`). Under D-KLN-39 an external ERP or PLM assigns and sometimes reassigns numbers, and a renumber must not be a source Change that touches released designs.

### R10-45 · Minor · Targets: ELX
**Section:** ELX Open questions 10
**Problem:** ELX defers the format question for large `Schematic` and `Layout` modules without a criterion for when to act.
**Evidence:** ELX OQ10: "if very large layouts parse too slowly, ING's binary sidecar keeps their semantics and changes only the file format".
**Fix:**
1. Keep both modules as text.
2. A 20-layer, 10,000-net board holds of the order of 10⁵ to 10⁶ one-line items, tens of megabytes (estimate). At 50 MB/s it parses in under 1 s (target), which ING's benchmark measures on the golden large board.
3. Add the binary sidecar only if that measurement exceeds 1 s, and keep text as the canonical form for merges.

## Verified claims

- MFG: ISA-95 Job Control defines eleven job-order methods, among them `StoreAndStart`, `Start`, `RevokeStart` and `Resume` | https://reference.opcfoundation.org/ISA95JOBCONTROL/v200/docs/6.3
- MFG: OPC 40001-3 (Machinery Job Management) is at 1.0.1 of 1 May 2024 | https://reference.opcfoundation.org/Machinery/Jobs/v100/docs/
- MFG: the EU Machinery Regulation applies from 20 January 2027 with cyber-safety provisions | https://single-market-economy.ec.europa.eu/sectors/mechanical-engineering/machinery_en
- MFG: Bambu Connect "removes slicing functions while enabling remote control and print initiation" | https://blog.bambulab.com/firmware-update-introducing-new-authorization-control-system-2/
- MFG: sparrow is MIT-licensed | https://github.com/JeroenGar/sparrow
- MFG, ELX: jagua-rs is MPL-2.0 | https://github.com/JeroenGar/jagua-rs
- MFG, ELX, ECO: Gerber Layer Format revision 2026.05 (19 May 2026), job format 2020.08, XNC 2021.11 | https://www.ucamco.com/en/gerber/downloads
- MFG: robot safety documentation cites ISO 10218-1:2025 and ISO 10218-2:2025 (marked [unverified] in the tab; both valid from 5 February 2025) | https://www.evs.ee/en/iso-10218-1-2025 and https://www.evs.ee/en/iso-10218-2-2025
- MFG: weld procedure records follow ISO 15614-1 and ISO 15609-1 ([unverified editions] in the tab; current editions are ISO 15614-1:2017 with Amd 1:2019 and ISO 15609-1:2019) | https://www.evs.ee/en/iso-15614-1-2017 and https://www.evs.ee/en/iso-15609-1-2019
- MFG, ECO: QIF 3.0 is ISO 23952:2020, and DMSC Model-Based Characteristics 1.0 was approved by ANSI on 24 June 2026 | https://qifstandards.org
- MFG: AIAG lists the PPAP manual under the identifier PPAP-4 | https://www.aiag.org/training-and-resources/manuals/details/PPAP-4
- MEC: ASME Y14.5-2018 is reaffirmed (R2024) and on stabilized maintenance | https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing
- MEC, KLN: ASME Y14.35-2025 is the current edition of the revision standard | https://www.asme.org/codes-standards/find-codes-standards/y14-35-revision-engineering-drawings-associated-documents
- ELX: the current KBL version (marked [unverified] in the tab) is KBL 2.5 SR-1 | https://ecad-wiki.prostep.org/specifications/kbl/
- ELX: derating follows ECSS-Q-ST-30-11C ([unverified: edition] in the tab; Rev.2 of 23 June 2021, superseding Rev.1) | https://ecss.nl/standard/ecss-q-st-30-11c-rev-2-derating-eee-components-23-june-2021/
