#!/usr/bin/env python3
"""Check spec tabs against the writing rules in docs/contract.md (sections 2, 10 and 11).

    python3 docs/tools/check.py docs/spec/06-mechanical.md     one or more tabs
    python3 docs/tools/check.py --all                          every file in docs/spec/
    python3 docs/tools/check.py docs/spec/06-mechanical.md --base round-1
                                                               also report what was cut since a git revision

Errors set the exit status to 1. Warnings are advice; fix them where the fix reads better.
A deliberate quotation of a forbidden term is allowed by a line in docs/tools/allow.txt.
"""
import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / "spec"
ALLOW = ROOT / "tools" / "allow.txt"

# Retired names and wrong vocabulary (revision brief, self-check).
FORBIDDEN = re.compile(
    r"cpu-f64|wgpu-f32|cuda-f64|rocm-f64|\bSBOM\b|Indeterminate|ExecMode|crucible\.lock|std::flux|std::elx"
    r"|std::sys\b|std::mat\b|std::phys\b|flux-field|flux-kernels|flux-bridges|anvil::bend|Zoo's patent"
    r"|\bCircuit\b|sign-off mode|Govern|epoch interruption|operation catalog"
)
FIDELITIES = {"Preview", "Interactive", "SignOff"}
BAD_FIDELITY = re.compile(r"\b(exact|coarse|draft|precise)\s+fidelity\b", re.I)
TAIL = [
    "State of the art", "Platform notes", "Interfaces with other subsystems", "Oracles",
    "Phasing", "Open questions", "Contract change requests", "Sources",
]
CAP_HEADER = ["Capability", "Contract", "Failure", "Oracle id", "Phase"]
TABS = {
    "01": "ING", "02": "ANV", "03": "FLX", "04": "COV", "05": "KLN", "06": "MEC",
    "07": "MFG", "08": "ELX", "09": "AGT", "10": "UIX", "11": "ECO", "12": "PLT",
}
WORD_FLOOR, WORD_CEILING = 12000, 18000
CEILING_BY_TAB = {"ING": 20000, "ANV": 20000}
HYPE = re.compile(r"\b(revolutionary|seamless(?:ly)?|cutting-edge|world-class|best-in-class|powerful|game-chang\w*)\b", re.I)
HTML = re.compile(
    r"<!--|</?(?:br|div|span|p|img|a|table|thead|tbody|tr|td|th|sup|sub|details|summary|b|i|em|strong|u|hr|ul|ol|li|pre|h[1-6])\b[^>]*>",
    re.I,
)
ORACLE_ID = re.compile(r"\b[A-Z]{3}-O-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
DECISION = re.compile(r"^\*\*Decision D-([A-Z]{3})-(\d+):\*\*")
OLD_DECISION = re.compile(r"^(?:\s*(?:[-*+]|\d+\.)\s+)?\*\*Decision D-[A-Z]{3}-(\d+):\*\*", re.M)
DIAGRAM = re.compile(r"\[\[DIAGRAM(?: ([^\]:\s]+))?: ([^\]]*)\]\]")
ABBREV = re.compile(r"\b(e\.g|i\.e|et al|vs|cf|Fig|Eq|No|approx|resp|incl|max|min|Ref|Sec)\.", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`*\"'(\[])")


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
        if re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            j = i + 1
            while j < len(lines) and lines[j].strip() and not re.match(r"^\s*([-*+]|\d+\.)\s+|^\s*(```|~~~)|^#{1,6}\s|^\s*\|", lines[j]):
                j += 1
            out.append(Block("item", i + 1, lines[i:j]))
            i = j
            continue
        if line.strip():
            j = i + 1
            while j < len(lines) and lines[j].strip() and not re.match(r"^\s*([-*+]|\d+\.)\s+|^\s*(```|~~~)|^#{1,6}\s|^\s*\|", lines[j]):
                j += 1
            out.append(Block("para", i + 1, lines[i:j]))
            i = j
            continue
        i += 1
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

    def error(self, line, msg):
        self.errors.append((line, msg))

    def warn(self, line, msg):
        self.warnings.append((line, msg))


def check(path, base=None):
    text = path.read_text()
    r = Report(path)
    blocks = blocks_of(text)
    lines = text.split("\n")
    allowed = [p for n, p in load_allow() if n == path.name]
    title = next((b for b in blocks if b.kind == "heading" and b.level == 1), None)
    tab = TABS.get(path.name[:2])
    if tab and (title is None or blocks[0] is not title):
        r.error(1, f"the file must start with its title: # <tab name> ({tab})")
        return r, text
    if tab and not title.text.endswith(f"({tab})"):
        r.error(1, f"title must end with the tab code ({tab})")

    # Names: retired vocabulary, Field arity, fidelity names, markup.
    in_code = set()
    for b in blocks:
        if b.kind == "code":
            in_code.update(range(b.start, b.start + len(b.lines)))
    for n, line in enumerate(lines, 1):
        for m in FORBIDDEN.finditer(line):
            if not any(p in line for p in allowed):
                r.error(n, f'retired or forbidden term "{m.group(0)}"')
        for m in re.finditer(r"\bFidelity::(\w+)", line):
            if m.group(1) not in FIDELITIES:
                r.error(n, f"fidelity name Fidelity::{m.group(1)}; use Preview, Interactive or SignOff")
        if n not in in_code:
            prose = strip_code_spans(line)
            for m in BAD_FIDELITY.finditer(prose):
                r.error(n, f'"{m.group(0)}" is not a fidelity name')
            for m in HTML.finditer(prose):
                r.error(n, f"HTML in markdown: {m.group(0)}")
            for m in HYPE.finditer(prose):
                r.warn(n, f'hype word "{m.group(0)}"')
            if "!" in re.sub(r"!\[|!=|\w!", "", prose):
                r.warn(n, "exclamation mark")
    for off, args in field_args(text):
        if len(args) >= 3:
            n = text.count("\n", 0, off) + 1
            r.error(n, f"Field with {len(args)} type parameters; use a product domain such as Field<(Body, Time), Temperature>")

    # Tables: every row has the header's number of cells.
    for b in blocks:
        if b.kind == "table":
            head, rows = table_rows(b)
            for k, row in enumerate(rows):
                if len(row) != len(head):
                    r.error(b.start + k + 2, f"table row has {len(row)} cells, header has {len(head)} (unescaped | ?)")

    # Diagrams.
    markers = [(text.count("\n", 0, m.start()) + 1, m.group(1)) for m in DIAGRAM.finditer(text)]
    if len(markers) > 2:
        r.error(markers[2][0], f"{len(markers)} diagrams; at most two per tab")
    for n, src in markers:
        if src and not (path.parent / src).exists():
            r.error(n, f"diagram source {src} does not exist")

    if not tab:
        r.notes.append("not a numbered subsystem tab: skeleton checks skipped")
        return r, text

    # Skeleton.
    sections, current = [], None
    for b in blocks:
        if b.kind == "heading" and b.level == 2:
            current = (b.text, b.start, [])
            sections.append(current)
        elif current is not None:
            current[2].append(b)
    names = [s[0] for s in sections]
    after_title = [b for b in blocks if b.start > title.start]
    if not after_title or after_title[0].kind != "para":
        r.error(title.start, "the lead must be a paragraph directly under the title, with no heading")
    elif len(sentences(after_title[0].body)) > 3:
        r.warn(after_title[0].start, "lead has more than three sentences")
    tail_found = [x for x in names if x in TAIL]
    if tail_found != TAIL:
        missing = [x for x in TAIL if x not in names]
        if missing:
            r.error(1, "missing sections: " + ", ".join(missing))
        if [x for x in TAIL if x in tail_found] != tail_found or len(tail_found) != len(set(tail_found)):
            r.error(1, "tail sections out of order or repeated: " + " · ".join(tail_found))
    if TAIL[0] in names:
        first_tail = names.index(TAIL[0])
        if any(x not in TAIL for x in names[first_tail:]):
            r.error(1, "design sections after State of the art: " + ", ".join(x for x in names[first_tail:] if x not in TAIL))
        design = sections[:first_tail]
    else:
        design = [s for s in sections if s[0] not in TAIL]
    if not design:
        r.error(1, "no design sections")

    # Capability tables: exactly one per design section, as its last block.
    referenced = {}
    for name, start, body in design:
        caps = [b for b in body if b.kind == "table" and table_rows(b)[0] == CAP_HEADER]
        if len(caps) != 1:
            r.error(start, f'design section "{name}" has {len(caps)} capability tables; it needs exactly one')
        elif body[-1] is not caps[0]:
            r.error(caps[0].start, f'capability table of "{name}" is not the last block of its section')
        for cap in caps:
            for k, row in enumerate(table_rows(cap)[1]):
                if len(row) == len(CAP_HEADER):
                    for oid in ORACLE_ID.findall(row[3]):
                        referenced.setdefault(oid, cap.start + k + 2)
                    if not row[4]:
                        r.error(cap.start + k + 2, f'capability "{row[0]}" has no phase')
    for name, start, body in sections[len(design):]:
        for b in body:
            if b.kind == "table" and table_rows(b)[0] == CAP_HEADER:
                r.error(b.start, f'capability table in "{name}"; capability tables belong to design sections')
    for n, line in enumerate(lines, 1):
        for oid in ORACLE_ID.findall(line):
            if oid.startswith(tab + "-"):
                referenced.setdefault(oid, n)

    # Oracles: each defined once, every reference defined.
    defined = {}
    oracle_sec = next((s for s in sections if s[0] == "Oracles"), None)
    if oracle_sec:
        for b in oracle_sec[2]:
            if b.kind == "table":
                for k, row in enumerate(table_rows(b)[1]):
                    for oid in oracle_ids_in_cell(row[0]):
                        if oid in defined:
                            r.error(b.start + k + 2, f"oracle {oid} defined twice")
                        defined.setdefault(oid, b.start + k + 2)
    for oid, n in sorted(referenced.items(), key=lambda kv: kv[1]):
        if oid not in defined and oid.startswith(tab + "-"):
            r.error(n, f"oracle {oid} is referenced but not defined under Oracles")
    in_tables = {o for o in referenced}
    for oid, n in defined.items():
        if oid not in in_tables:
            r.warn(n, f"oracle {oid} is defined but no capability cites it")

    # Decisions.
    decisions = {}
    for b in blocks:
        if b.kind in ("para", "item"):
            m = DECISION.match(re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", b.body))
            if m:
                code, num = m.group(1), int(m.group(2))
                if code != tab:
                    r.error(b.start, f"decision D-{code}-{num} in a {tab} tab")
                if num in decisions:
                    r.error(b.start, f"decision D-{code}-{num} appears twice")
                decisions.setdefault(num, b.start)
                if "*Why:*" not in b.body or "*Rejected:*" not in b.body:
                    r.warn(b.start, f"decision D-{code}-{num} lacks *Why:* or *Rejected:*")
    if decisions:
        gaps = sorted(set(range(1, max(decisions) + 1)) - set(decisions))
        if gaps:
            r.warn(1, "decision numbers missing: " + ", ".join(f"D-{tab}-{g}" for g in gaps))

    # Length and style.
    body = text.split("\n## Sources")[0]
    words = len(re.findall(r"\S+", body))
    ceiling = CEILING_BY_TAB.get(tab, WORD_CEILING)
    if not WORD_FLOOR <= words <= ceiling:
        r.warn(1, f"{words:,} words excluding Sources; the range is {WORD_FLOOR:,} to {ceiling:,}")
    long_sentences, long_paras = [], []
    sources_line = next((s[1] for s in sections if s[0] == "Sources"), len(lines) + 1)
    for b in blocks:
        if b.kind in ("para", "item") and b.start < sources_line and not b.body.lstrip().startswith("[[DIAGRAM"):
            ss = sentences(strip_code_spans(" ".join(x.strip() for x in b.lines)))
            if b.kind == "para" and len(ss) > 3:
                long_paras.append(b.start)
            long_sentences += [b.start for s in ss if len(s.split()) > 25]
    def where(ns):
        ns = sorted(set(ns))
        return ", ".join(map(str, ns[:10])) + (", …" if len(ns) > 10 else "")
    if long_sentences:
        r.warn(long_sentences[0], f"{len(long_sentences)} sentences over 25 words (lines {where(long_sentences)})")
    if long_paras:
        r.warn(long_paras[0], f"{len(long_paras)} paragraphs over three sentences (lines {where(long_paras)})")

    r.notes.append(
        f"{tab} · {words:,} words excluding Sources · {len(design)} design sections · "
        f"{len(decisions)} decisions · {len(defined)} oracles"
    )

    # Nothing cut since the base revision.
    if base:
        rel = path.resolve().relative_to(ROOT).as_posix()
        try:
            old = subprocess.run(["git", "-C", str(ROOT), "show", f"{base}:./{rel}"], capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError:
            r.notes.append(f"{rel} does not exist at {base}")
            return r, text
        old_decisions = {int(m.group(1)) for m in OLD_DECISION.finditer(old)}
        cut = sorted(old_decisions - set(decisions))
        if cut:
            r.error(1, f"decisions present at {base} but missing now: " + ", ".join(f"D-{tab}-{c}" for c in cut))
        old_oracles = {m.group(0) for m in ORACLE_ID.finditer(old) if m.group(0).startswith(tab + "-")}
        gone = sorted(old_oracles - set(defined) - set(referenced))
        if gone:
            r.warn(1, f"{len(gone)} oracle ids at {base} no longer appear (renamed or merged? say so in the commit): " + ", ".join(gone[:12]) + (" …" if len(gone) > 12 else ""))
        def source_count(t):
            sec = t.split("\n## Sources", 1)
            return len(re.findall(r"https?://", sec[1])) if len(sec) > 1 else 0
        before, after = source_count(old), source_count(text)
        if after < before:
            r.warn(1, f"Sources lists {after} links, {before} at {base}; never cut a source")
    return r, text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=pathlib.Path)
    ap.add_argument("--all", action="store_true", help="check every file in docs/spec/")
    ap.add_argument("--base", help="git revision to compare against (for example round-1)")
    ap.add_argument("-q", "--quiet", action="store_true", help="print errors and the summary only")
    args = ap.parse_args()
    files = sorted(SPEC.glob("[0-9][0-9]-*.md")) if args.all else args.files
    if not files:
        ap.error("name a file or pass --all")
    failed = False
    for f in files:
        rep, _ = check(f, args.base)
        status = "FAIL" if rep.errors else "ok"
        shown = f.resolve().relative_to(ROOT) if str(f.resolve()).startswith(str(ROOT)) else f
        print(f"{status:4}  {shown}  ({len(rep.errors)} errors, {len(rep.warnings)} warnings)")
        for note in rep.notes:
            print(f"      {note}")
        for n, msg in rep.errors:
            print(f"      error    l.{n}: {msg}")
        if not args.quiet:
            for n, msg in rep.warnings:
                print(f"      warning  l.{n}: {msg}")
        failed |= bool(rep.errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
