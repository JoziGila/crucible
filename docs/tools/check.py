#!/usr/bin/env python3
"""Check spec tabs against the writing rules of docs/contract.md (sections 2, 10, 11 and 13.4).

    python3 docs/tools/check.py docs/spec/06-mechanical.md     one or more tabs
    python3 docs/tools/check.py --all                          every file in docs/spec/
    python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-3
                                                               also report what was cut since a git revision

Each error and warning names its rule in brackets. Errors set the exit status to 1; warnings are
advice, fixed where the fix reads better. A deliberate use of a forbidden term or history word is
allowed by a line in docs/tools/allow.txt.

Prerequisites (contract 13.4): a capability row that needs another tab's capability ends one of its
cells with `Requires: <TAB> <capability>`, several separated by ";". <capability> is the other row's
Capability cell, word for word (case, `*` and link targets ignored). The row's phase may not be
earlier than the phase of any row it requires; the first digit of a Phase cell is its phase.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec"
ALLOW = ROOT / "tools" / "allow.txt"

TABS = {
    "01": "ING", "02": "ANV", "03": "FLX", "04": "COV", "05": "KLN", "06": "MEC",
    "07": "MFG", "08": "ELX", "09": "AGT", "10": "UIX", "11": "ECO", "12": "PLT",
}
# Retired names (contract 2 "Never call it" phrases with one meaning, and section 18's deletions).
FORBIDDEN = re.compile(
    r"cpu-f64|wgpu-f32|cuda-f64|rocm-f64|\bSBOM\b|Indeterminate|ExecMode|crucible\.lock|std::flux|std::elx"
    r"|std::sys\b|std::mat\b|std::phys\b|flux-field|flux-kernels|flux-bridges|anvil::bend|Zoo's patent"
    r"|\bCircuit\b|sign-off mode|Govern|epoch interruption|operation catalog"
    r"|\bOpKey\b|DiagnosticSeverity|conditional_on|grant_deviation|\bon_(?:merge|partial|fragile)\b|\bLoro\b"
    r"|(?i:evidence (?:level|watermark)|fidelity level|measurement cell|hardware result|external tool run"
    r"|out-of-process result|taint flags|classification tags|site policy|execution mode|interactive (?:edit )?lane)"
)
FIDELITIES = {"Preview", "Interactive", "SignOff"}
BAD_FIDELITY = re.compile(r"\b(exact|coarse|draft|precise)\s+fidelity\b", re.I)
HISTORY = re.compile(r"\bR\d{1,2}-\d{2,3}\b|(?i:\bround[- ]\d+\b|\bformerly\b|\breplaces\b)")
TAIL = [
    "State of the art", "Platform notes", "Interfaces with other subsystems", "Oracles",
    "Phasing", "Open questions", "Contract change requests", "Sources",
]
HISTORY_TABS = {"13", "14"}  # the Adversarial review and Decisions log, which record retired names
NOT_PROSE = {"Reference", "State of the art", "Interfaces with other subsystems", "Oracles", "Sources"}
CAP_HEADER = ["Capability", "Contract", "Failure", "Oracle id", "Phase"]
INTERFACE_HEADER = ["To", "What", "Types", "Phase"]
ORACLE_HEADER = ["Id", "Verifies", "Pass criterion"]
SOURCE_HEADER = ["Key", "Title", "URL", "Date opened"]
WORD_FLOOR, WORD_CEILING = 9000, 15000
CEILING_BY_TAB = {"ING": 17000, "ANV": 17000}
HYPE = re.compile(r"\b(revolutionary|seamless(?:ly)?|cutting-edge|world-class|best-in-class|powerful|game-chang\w*)\b", re.I)
HTML = re.compile(
    r"<!--|</?(?:br|div|span|p|img|a|table|thead|tbody|tr|td|th|sup|sub|details|summary|b|i|em|strong|u|hr|ul|ol|li|pre|h[1-6])\b[^>]*>",
    re.I,
)
ORACLE_ID = re.compile(r"\b[A-Z]{3}-O-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
DECISION_LINE = re.compile(r"^(\s*(?:[-*+]|\d+\.)\s+)?\*\*Decision D-([A-Z]{3})-(\d+):\*\*")
DIAGRAM = re.compile(r"\[\[DIAGRAM(?: ([^\]:\s]+))?: ([^\]]*)\]\]")
ABBREV = re.compile(r"\b(e\.g|i\.e|et al|vs|cf|Fig|Eq|No|approx|resp|incl|max|min|Ref|Sec)\.", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`*\"'(\[])")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# Names a provides row may use in its To cell, besides the tab codes.
TO_NAMES = {"ingot": "ING", "anvil": "ANV", "flux": "FLX", "kiln": "KLN", "repo": "KLN", "plm": "KLN",
            "trust": "KLN", "api": "AGT"}


# ---------------------------------------------------------------- parsing

class Block:
    def __init__(self, kind, start, lines, level=0, text=""):
        self.kind, self.start, self.lines, self.level, self.text = kind, start, lines, level, text

    @property
    def body(self):
        return "\n".join(self.lines)


def blocks_of(text):
    """Split markdown into heading, code, table, list item and paragraph blocks (1-based line numbers)."""
    out, lines, i = [], text.split("\n"), 0
    stop = re.compile(r"^\s*([-*+]|\d+\.)\s+|^\s*(```|~~~)|^#{1,6}\s|^\s*\|")
    while i < len(lines):
        line = lines[i]
        fence = re.match(r"^\s*(```|~~~)", line)
        if fence:
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith(fence.group(1)):
                j += 1
            out.append(Block("code", i + 1, lines[i:j + 1]))
            i = j + 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            out.append(Block("heading", i + 1, [line], len(heading.group(1)), heading.group(2).strip()))
            i += 1
            continue
        if line.lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            out.append(Block("table", i + 1, lines[i:j]))
            i = j
            continue
        if line.strip():
            kind = "item" if re.match(r"^\s*([-*+]|\d+\.)\s+", line) else "para"
            j = i + 1
            while j < len(lines) and lines[j].strip() and not stop.match(lines[j]):
                j += 1
            out.append(Block(kind, i + 1, lines[i:j]))
            i = j
            continue
        i += 1
    return out


def sections_of(blocks):
    """(lead blocks, [(name, start line, blocks)]) for the level-2 sections of a tab."""
    lead, sections, current = [], [], None
    for b in blocks:
        if b.kind == "heading" and b.level == 1:
            continue
        if b.kind == "heading" and b.level == 2:
            current = (b.text, b.start, [])
            sections.append(current)
        elif current is None:
            lead.append(b)
        else:
            current[2].append(b)
    return lead, sections


def design_sections(sections):
    """Sections before the optional Reference section and the fixed tail."""
    out = []
    for s in sections:
        if s[0] == "Reference" or s[0] in TAIL:
            break
        out.append(s)
    return out


def cells(row):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", row)]


def table_rows(block):
    rows = [cells(r) for r in block.lines]
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", c) for c in rows[1] if c):
        return rows[0], rows[2:]
    return rows[0], rows[1:]


def strip_code_spans(s):
    return re.sub(r"`[^`]*`", "``", s)


def sentences(s):
    s = ABBREV.sub(lambda m: m.group(0).replace(".", "․"), s)
    return [x for x in SENTENCE_SPLIT.split(s.strip()) if x.strip()]


def norm(s):
    return re.sub(r"\s+", " ", LINK.sub(r"\1", s).replace("*", "")).strip().rstrip(".").lower()


def phase_of(cell):
    m = re.search(r"\d", cell)
    return int(m.group(0)) if m else None


def tabs_named(cell):
    """Tab codes a To cell names (codes, engine and crate names, or every tab)."""
    if re.search(r"\b(?:all|every)\b", cell, re.I) and re.search(r"\b(?:tabs?|subsystems?)\b", cell, re.I):
        return sorted(set(TABS.values()))
    found = set(re.findall(r"\b(" + "|".join(TABS.values()) + r")\b", cell))
    found |= {code for name, code in TO_NAMES.items() if re.search(r"\b" + name + r"\b", cell, re.I)}
    return sorted(found)


def field_args(text):
    """Yield (offset, args) for every Field<...> with its top-level type arguments."""
    for m in re.finditer(r"\bField<", text):
        depth, j, args, cur = 1, m.end(), [], ""
        while j < len(text) and depth:
            ch = text[j]
            if ch in "<([":
                depth += 1
            elif ch in ">)]":
                depth -= 1
                if depth == 0:
                    break
            if ch == "," and depth == 1:
                args.append(cur.strip())
                cur = ""
            else:
                cur += ch
            j += 1
        args.append(cur.strip())
        yield m.start(), args


def oracle_ids_in_cell(cell):
    """Oracle ids named in a cell, expanding ranges such as ANV-O-OP-1 to ANV-O-OP-8."""
    ids, pat = [], ORACLE_ID.pattern.replace(r"\b", "")
    for m in re.finditer(r"\b(" + pat + r")(?:\s*(?:to|–|…)\s*(" + pat + r"))?\b", cell):
        first, last = m.group(1), m.group(2)
        a = re.match(r"(.*-)(\d+)$", first)
        b = re.match(r"(.*-)(\d+)$", last) if last else None
        if a and b and a.group(1) == b.group(1):
            ids += [f"{a.group(1)}{n}" for n in range(int(a.group(2)), int(b.group(2)) + 1)]
        else:
            ids += [x for x in (first, last) if x]
    return ids


def capability_tables(design):
    """(section name, table block, rows) for every table with the capability header."""
    for name, _, body in design:
        for b in body:
            if b.kind == "table" and table_rows(b)[0] == CAP_HEADER:
                yield name, b, table_rows(b)[1]


def capability_index(paths):
    """{tab: {normalized capability: (phase, name)}} over the given tabs."""
    index = {}
    for p in paths:
        tab = TABS.get(p.name[:2])
        if not tab:
            continue
        _, sections = sections_of(blocks_of(p.read_text()))
        rows = index.setdefault(tab, {})
        for _, _, table in capability_tables(design_sections(sections)):
            for row in table:
                if len(row) == len(CAP_HEADER):
                    rows.setdefault(norm(row[0]), (phase_of(row[4]), row[0]))
    return index


def requires_of(row):
    """[(tab, capability)] named by `Requires:` entries in a capability row."""
    out = []
    for cell in row:
        _, sep, rest = cell.partition("Requires:")
        for ref in rest.split(";") if sep else []:
            m = re.match(r"\s*([A-Z]{3})\s+(.+)", LINK.sub(r"\1", ref))
            out.append((m.group(1), m.group(2).strip()) if m else ("", ref.strip()))
    return out


def load_allow():
    allowed = []
    if ALLOW.exists():
        for line in ALLOW.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                name, _, phrase = line.partition(" ")
                allowed.append((name, phrase.strip()))
    return allowed


# ---------------------------------------------------------------- checks

class Report:
    def __init__(self, path):
        self.path, self.errors, self.warnings, self.notes = path, [], [], []

    def error(self, line, rule, msg):
        self.errors.append((line, rule, msg))

    def warn(self, line, rule, msg):
        self.warnings.append((line, rule, msg))


def check(path, base=None, index=None):
    text = path.read_text()
    r = Report(path)
    blocks = blocks_of(text)
    lines = text.split("\n")
    allowed = [p for n, p in load_allow() if n == path.name]
    title = next((b for b in blocks if b.kind == "heading" and b.level == 1), None)
    tab = TABS.get(path.name[:2])
    history_tab = path.name[:2] in HISTORY_TABS
    if tab and (title is None or blocks[0] is not title):
        r.error(1, "skeleton", f"the file must start with its title: # <tab name> ({tab})")
        return r
    if tab and not title.text.endswith(f"({tab})"):
        r.error(1, "skeleton", f"title must end with the tab code ({tab})")
    lead, sections = sections_of(blocks)
    names = [s[0] for s in sections]
    in_code = set()
    for b in blocks:
        if b.kind == "code":
            in_code.update(range(b.start, b.start + len(b.lines)))
    open_q = next((s[1] for s in sections if s[0] == "Open questions"), len(lines) + 1)

    # Names, fidelities, markup, voice and review history.
    for n, line in enumerate(lines, 1):
        ok = any(p in line for p in allowed)
        for m in FORBIDDEN.finditer(line):
            if not ok and not history_tab:
                r.error(n, "names", f'retired or forbidden term "{m.group(0)}"')
        for m in re.finditer(r"\bFidelity::(\w+)", line):
            if m.group(1) not in FIDELITIES:
                r.error(n, "names", f"fidelity name Fidelity::{m.group(1)}; use Preview, Interactive or SignOff")
        if n in in_code:
            continue
        prose = strip_code_spans(line)
        for m in BAD_FIDELITY.finditer(prose):
            r.error(n, "names", f'"{m.group(0)}" is not a fidelity name')
        for m in HTML.finditer(prose):
            r.error(n, "html", f"HTML in markdown: {m.group(0)}")
        for m in HYPE.finditer(prose):
            r.warn(n, "voice", f'hype word "{m.group(0)}"')
        if "!" in re.sub(r"!\[|!=|\w!", "", prose):
            r.warn(n, "voice", "exclamation mark")
        if tab and n < open_q and not ok:
            for m in HISTORY.finditer(LINK.sub(r"\1", prose)):
                r.error(n, "history", f'review history "{m.group(0)}" above Open questions')
    for off, args in field_args(text):
        if len(args) >= 3:
            n = text.count("\n", 0, off) + 1
            r.error(n, "names", f"Field with {len(args)} type parameters; use a product domain such as Field<(Body, Time), Temperature>")

    # Tables: every row has the header's number of cells.
    for b in blocks:
        if b.kind == "table":
            head, rows = table_rows(b)
            for k, row in enumerate(rows):
                if len(row) != len(head):
                    r.error(b.start + k + 2, "tables", f"table row has {len(row)} cells, header has {len(head)} (unescaped | ?)")

    # Diagrams.
    markers = [(text.count("\n", 0, m.start()) + 1, m.group(1)) for m in DIAGRAM.finditer(text)]
    if len(markers) > 2:
        r.error(markers[2][0], "diagrams", f"{len(markers)} diagrams; at most two per tab")
    for n, src in markers:
        if src and not (path.parent / src).exists():
            r.error(n, "diagrams", f"diagram source {src} does not exist")

    if not tab:
        r.notes.append("not a numbered subsystem tab: skeleton checks skipped")
        return r

    # Skeleton: lead, design sections, optional Reference, then the fixed tail.
    expected = ["Reference"] + TAIL if "Reference" in names else TAIL
    design = design_sections(sections)
    rest = names[len(design):]
    if rest != expected:
        missing = [x for x in expected if x not in rest]
        extra = [x for x in rest if x not in expected]
        msg = "after the design sections the order is " + " · ".join(expected)
        if missing:
            msg += "; missing: " + ", ".join(missing)
        if extra:
            msg += "; not allowed here: " + ", ".join(extra)
        r.error(sections[len(design)][1] if rest else 1, "skeleton", msg)
    if not design:
        r.error(1, "skeleton", "no design sections")

    # Lead: one paragraph of three sentences, no heading.
    if not lead or [b.kind for b in lead] != ["para"]:
        r.error(title.start + 1, "lead", "the lead is one paragraph directly under the title")
    if lead and lead[0].kind == "para":
        k = len(sentences(strip_code_spans(" ".join(x.strip() for x in lead[0].lines))))
        if k != 3:
            r.error(lead[0].start, "lead", f"the lead has {k} sentences; it has three")

    # Design sections: open with why, end with one capability table.
    referenced = {}
    for i, (name, start, body) in enumerate(design):
        if not body or body[0].kind != "para":
            r.error(start, "design", f'"{name}" does not open with a sentence saying why it exists')
        caps = [b for b in body if b.kind == "table" and table_rows(b)[0] == CAP_HEADER]
        if len(caps) != 1:
            r.error(start, "capabilities", f'"{name}" has {len(caps)} capability tables; it ends with exactly one')
        elif body[-1] is not caps[0]:
            r.error(caps[0].start, "capabilities", f'the capability table of "{name}" is not the last block of its section')
        for b in body:
            head = table_rows(b)[0] if b.kind == "table" else []
            if head and head[0] == "Capability" and head != CAP_HEADER:
                r.error(b.start, "capabilities", "capability table header is " + " · ".join(head) + "; use " + " · ".join(CAP_HEADER))
    if design and not re.search(r"bracket|\bGP\d", "\n".join(b.body for b in design[0][2])):
        r.warn(design[0][1], "design", "the first design section has no worked example on the canonical bracket or a golden product")
    for name, start, body in sections[len(design):]:
        for b in body:
            if b.kind == "table" and table_rows(b)[0] == CAP_HEADER:
                r.error(b.start, "capabilities", f'capability table in "{name}"; capability tables end design sections')

    # Capability rows: Failure, Oracle id, Phase and Requires.
    index = index if index is not None else capability_index(sorted(SPEC.glob("[0-9][0-9]-*.md")))
    capabilities = 0
    for name, cap, rows in capability_tables(design):
        for k, row in enumerate(rows):
            n = cap.start + k + 2
            if len(row) != len(CAP_HEADER):
                continue
            capabilities += 1
            what, failure, oracles, phase = row[0], row[2], row[3], row[4]
            if not failure or re.fullmatch(r"[-–—]+", failure) or (failure.startswith("None") and not failure.startswith("None:")):
                r.error(n, "capabilities", f'"{what}": the Failure cell names a typed failure or reads "None: <why it cannot fail>"')
            ids = ORACLE_ID.findall(oracles)
            if not ids:
                r.error(n, "capabilities", f'"{what}" names no oracle id')
            for oid in ids:
                referenced.setdefault(oid, n)
            if phase_of(phase) is None:
                r.error(n, "capabilities", f'"{what}" has no phase')
            for other, need in requires_of(row):
                target = index.get(other, {}).get(norm(need))
                if target is None:
                    r.error(n, "requires", f'"{what}" requires "{other} {need}", which is no capability row of {other or "a tab"}')
                elif None not in (target[0], phase_of(phase)) and phase_of(phase) < target[0]:
                    r.error(n, "requires", f'"{what}" is phase {phase_of(phase)} but requires {other} "{target[1]}" at phase {target[0]}')
    for n, line in enumerate(lines, 1):
        for oid in ORACLE_ID.findall(line):
            if oid.startswith(tab + "-"):
                referenced.setdefault(oid, n)

    # Interfaces: one provides table, To · What · Types · Phase.
    sec = dict((s[0], s) for s in sections)
    if "Interfaces with other subsystems" in sec:
        _, start, body = sec["Interfaces with other subsystems"]
        tables = [b for b in body if b.kind == "table"]
        if len(tables) != 1:
            r.error(start, "interfaces", f"Interfaces has {len(tables)} tables; it has one: " + " · ".join(INTERFACE_HEADER))
        for b in tables:
            head, rows = table_rows(b)
            if head != INTERFACE_HEADER:
                r.error(b.start, "interfaces", "Interfaces table header is " + " · ".join(head) + "; use " + " · ".join(INTERFACE_HEADER))
                continue
            for k, row in enumerate(rows):
                if len(row) == 4 and not tabs_named(row[0]):
                    r.error(b.start + k + 2, "interfaces", f'To cell "{row[0]}" names no tab')
                if len(row) == 4 and phase_of(row[3]) is None:
                    r.error(b.start + k + 2, "interfaces", f'"{row[1][:60]}" has no phase')

    # Oracles: Id · Verifies · Pass criterion, each defined once, every reference defined.
    defined = {}
    if "Oracles" in sec:
        for b in sec["Oracles"][2]:
            if b.kind != "table":
                continue
            head, rows = table_rows(b)
            if head != ORACLE_HEADER:
                r.error(b.start, "oracles", "Oracles table header is " + " · ".join(head) + "; use " + " · ".join(ORACLE_HEADER))
            for k, row in enumerate(rows):
                for oid in oracle_ids_in_cell(row[0]):
                    if oid in defined:
                        r.error(b.start + k + 2, "oracles", f"oracle {oid} defined twice")
                    defined.setdefault(oid, b.start + k + 2)
    for oid, n in sorted(referenced.items(), key=lambda kv: kv[1]):
        if oid not in defined and oid.startswith(tab + "-"):
            r.error(n, "oracles", f"oracle {oid} is referenced but not defined under Oracles")
    for oid, n in defined.items():
        if oid not in referenced:
            r.warn(n, "oracles", f"oracle {oid} is defined but no capability cites it")

    # Sources: Key · Title · URL · Date opened.
    if "Sources" in sec:
        tables = [b for b in sec["Sources"][2] if b.kind == "table"]
        if [table_rows(b)[0] for b in tables] != [SOURCE_HEADER]:
            r.error(sec["Sources"][1], "sources", "Sources is one table: " + " · ".join(SOURCE_HEADER))

    # Decisions: the three-line block, numbered for this tab, each number once.
    decisions = {}
    for b in blocks:
        if b.kind not in ("para", "item"):
            continue
        for j, line in enumerate(b.lines):
            m = DECISION_LINE.match(line)
            if not m:
                continue
            code, num, n = m.group(2), int(m.group(3)), b.start + j
            if code != tab:
                r.error(n, "decisions", f"decision D-{code}-{num} in a {tab} tab")
            if num in decisions:
                r.error(n, "decisions", f"decision D-{code}-{num} appears twice")
            decisions.setdefault(num, n)
            shape = (b.kind == "para" and j == 0 and len(b.lines) == 3 and not m.group(1)
                     and b.lines[1].startswith("*Why:* ") and b.lines[2].startswith("*Rejected:* "))
            if not shape:
                r.error(n, "decisions", f"D-{code}-{num} is not a paragraph of three lines: **Decision …:**, *Why:*, *Rejected:*")
    if decisions:
        gaps = sorted(set(range(1, max(decisions) + 1)) - set(decisions))
        if gaps:
            r.warn(1, "decisions", "decision numbers missing: " + ", ".join(f"D-{tab}-{g}" for g in gaps))

    # Length: words of paragraphs, list items and tables other than capability tables,
    # outside the excluded sections; headings, code and diagram markers do not count.
    counted = lead + [b for s in sections if s[0] not in NOT_PROSE for b in s[2]]
    def prose_words(b):
        if b.kind in ("para", "item") and not b.body.lstrip().startswith("[[DIAGRAM"):
            return len(LINK.sub(r"\1", b.body).split())
        if b.kind == "table" and table_rows(b)[0] != CAP_HEADER:
            head, rows = table_rows(b)
            return sum(len(LINK.sub(r"\1", c).split()) for row in [head] + rows for c in row)
        return 0
    words = sum(prose_words(b) for b in counted)
    ceiling = CEILING_BY_TAB.get(tab, WORD_CEILING)
    if not WORD_FLOOR <= words <= ceiling:
        r.error(1, "length", f"{words:,} words of prose; the range is {WORD_FLOOR:,} to {ceiling:,}")

    # Style advice: sentences over 25 words, paragraphs over five sentences.
    long_sentences, long_paras = [], []
    for b in counted:
        if b.kind in ("para", "item") and not b.body.lstrip().startswith("[[DIAGRAM"):
            ss = sentences(strip_code_spans(" ".join(x.strip() for x in b.lines)))
            if b.kind == "para" and len(ss) > 5:
                long_paras.append(b.start)
            long_sentences += [b.start for s in ss if len(s.split()) > 25]

    def where(ns):
        ns = sorted(set(ns))
        return ", ".join(map(str, ns[:10])) + (", …" if len(ns) > 10 else "")
    if long_sentences:
        r.warn(long_sentences[0], "style", f"{len(long_sentences)} sentences over 25 words (lines {where(long_sentences)})")
    if long_paras:
        r.warn(long_paras[0], "style", f"{len(long_paras)} paragraphs over five sentences (lines {where(long_paras)})")

    r.notes.append(
        f"{tab} · {words:,} words of prose · {len(design)} design sections · {capabilities} capabilities · "
        f"{len(decisions)} decisions · {len(defined)} oracles"
    )

    # Nothing cut since the base revision.
    if base:
        rel = path.resolve().relative_to(ROOT).as_posix()
        try:
            old = subprocess.run(["git", "-C", str(ROOT), "show", f"{base}:./{rel}"], capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError:
            r.notes.append(f"{rel} does not exist at {base}")
            return r
        cut = sorted({int(m.group(3)) for m in re.finditer(DECISION_LINE.pattern, old, re.M)} - set(decisions))
        if cut:
            r.error(1, "decisions", f"decisions present at {base} but missing now: " + ", ".join(f"D-{tab}-{c}" for c in cut))
        old_oracles = {m.group(0) for m in ORACLE_ID.finditer(old) if m.group(0).startswith(tab + "-")}
        gone = sorted(old_oracles - set(defined) - set(referenced))
        if gone:
            r.warn(1, "cut", f"{len(gone)} oracle ids at {base} no longer appear (renamed or merged? say so in the report): " + ", ".join(gone[:12]) + (" …" if len(gone) > 12 else ""))
        old_caps = sum(len(rows) for _, _, rows in capability_tables(design_sections(sections_of(blocks_of(old))[1])))
        if capabilities < old_caps:
            r.warn(1, "cut", f"{capabilities} capability rows, {old_caps} at {base}; never cut a capability (merged rows are fine)")
        urls = lambda t: set(re.findall(r"https?://[^\s)>|\]]+", t.split("\n## Sources", 1)[-1])) if "\n## Sources" in t else set()
        lost = sorted(urls(old) - urls(text))
        if lost:
            r.warn(1, "cut", f"{len(lost)} source URLs at {base} no longer in Sources; never cut a source whose claim stays: " + ", ".join(lost[:5]) + (" …" if len(lost) > 5 else ""))
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=pathlib.Path)
    ap.add_argument("--all", action="store_true", help="check every file in docs/spec/")
    ap.add_argument("--base", help="git revision to compare against (for example round-3)")
    ap.add_argument("-q", "--quiet", action="store_true", help="print errors and the summary only")
    args = ap.parse_args()
    files = sorted(SPEC.glob("[0-9][0-9]-*.md")) if args.all else args.files
    if not files:
        ap.error("name a file or pass --all")
    index = capability_index(sorted(SPEC.glob("[0-9][0-9]-*.md")))
    failed = False
    for f in files:
        rep = check(f, args.base, index)
        status = "FAIL" if rep.errors else "ok"
        shown = f.resolve().relative_to(ROOT) if str(f.resolve()).startswith(str(ROOT)) else f
        print(f"{status:4}  {shown}  ({len(rep.errors)} errors, {len(rep.warnings)} warnings)")
        for note in rep.notes:
            print(f"      {note}")
        for n, rule, msg in rep.errors:
            print(f"      error    [{rule}] l.{n}: {msg}")
        if not args.quiet:
            for n, rule, msg in rep.warnings:
                print(f"      warning  [{rule}] l.{n}: {msg}")
        failed |= bool(rep.errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
