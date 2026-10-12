#!/usr/bin/env python3
"""Generate views of the subsystem tabs into docs/build/extracts/.

    python3 docs/tools/extract.py

    decisions.md       every decision with its *Why:* line, by tab (for the Decisions log)
    ccr.md             every tab's Contract change requests (for the ruling step)
    requires.md        what each tab requires: the other tabs' Interfaces rows whose To cell names it
                       (contract 11), and rows whose To cell names no tab
    open-questions.md  every tab's Open questions
    glossary.md        the Overview's glossary (contract 11): each abbreviation the tabs spell out,
                       one line with its expansion and its owner, the tab that uses it most
"""
import collections
import re

from check import INTERFACE_HEADER, ROOT, SPEC, TABS, blocks_of, sections_of, table_rows, tabs_named

OUT = ROOT / "build" / "extracts"
DECISION = re.compile(r"^(?:\s*(?:[-*+]|\d+\.)\s+)?(\*\*Decision D-[A-Z]{3}-\d+:\*\*.*(?:\n\*Why:\*.*)?)$", re.M)
SHORT = re.compile(r"[A-Za-z][A-Za-z0-9&/-]{1,9}")


def long_form(short, text):
    """Schwartz and Hearst (2003): the shortest tail of text whose letters spell short, or None."""
    s, l = len(short) - 1, len(text) - 1
    while s >= 0:
        c = short[s].lower()
        if not c.isalnum():
            s -= 1
            continue
        while l >= 0 and (text[l].lower() != c or (s == 0 and l > 0 and text[l - 1].isalnum())):
            l -= 1
        if l < 0:
            return None
        l, s = l - 1, s - 1
    found = text[text.rfind(" ", 0, l + 1) + 1:].strip()
    if len(found) <= len(short) or re.search(r"[,;|\[\]]", found) or not re.search(r"[ -]", found):
        return None
    return found


def abbreviations(prose):
    """(short, long) pairs written as "long form (SHORT)" or "SHORT (long form)"."""
    for m in re.finditer(r"([^()|]*?)\s\(([^()|]+)\)", prose):
        before, inside = m.group(1), m.group(2).strip()
        if SHORT.fullmatch(inside) and sum(ch.isupper() for ch in inside) >= 2:
            words = before.split()
            found = long_form(inside, " ".join(words[-min(len(inside) + 5, 2 * len(inside)):]))
            if found:
                yield inside, found
        elif before.split() and SHORT.fullmatch(before.split()[-1]) and sum(ch.isupper() for ch in before.split()[-1]) >= 2:
            short, text = before.split()[-1], re.split(r"[,;:]", inside)[0]
            text = re.sub(r"^(?:an?|the)\s+", "", text)
            found = long_form(short, text)
            if found and len(text.split()) >= 2:
                yield short, found


def main():
    parts = collections.defaultdict(list)
    provides, texts, expansions = [], {}, {}
    tabs = [(TABS[f.name[:2]], f) for f in sorted(SPEC.glob("[0-9][0-9]-*.md")) if f.name[:2] in TABS]
    for tab, f in tabs:
        t = f.read_text()
        blocks = blocks_of(t)
        _, sections = sections_of(blocks)
        sec = {name: body for name, _, body in sections}
        text_of = lambda name: "\n\n".join(b.body for b in sec.get(name, [])).strip()
        decisions = DECISION.findall(t)
        parts["decisions"].append(f"### {tab} ({len(decisions)} decisions)\n\n" + "\n\n".join(decisions))
        parts["ccr"].append(f"### {tab}\n\n" + text_of("Contract change requests"))
        parts["open-questions"].append(f"### {tab}\n\n" + text_of("Open questions"))
        shaped = [b for b in sec.get("Interfaces with other subsystems", []) if b.kind == "table" and table_rows(b)[0] == INTERFACE_HEADER]
        if not shaped:
            parts["requires-skipped"].append(tab)
        for b in shaped:
            provides += [(tab, row) for row in table_rows(b)[1] if len(row) == 4]
        written = [b for b in blocks if b.kind in ("para", "item", "table") and b not in sec.get("Sources", [])]
        prose = re.sub(r"`[^`]*`|https?://\S+", "", " ".join(" ".join(x.strip() for x in b.lines) for b in written))
        for short, found in abbreviations(prose):
            if short not in TABS.values():
                expansions.setdefault(short, (tab, found))
        texts[tab] = t

    requires = []
    for tab, _ in tabs:
        rows = [f"| {src} | {row[1]} | {row[2]} | {row[3]} |" for src, row in provides if src != tab and tab in tabs_named(row[0])]
        requires.append(f"### {tab} requires\n\n| From | What | Types | Phase |\n| --- | --- | --- | --- |\n" + "\n".join(rows))
    orphans = [f"| {src} | {row[0]} | {row[1]} |" for src, row in provides if not tabs_named(row[0])]
    if orphans:
        requires.append("### Rows whose To cell names no tab\n\n| From | To | What |\n| --- | --- | --- |\n" + "\n".join(orphans))
    if parts["requires-skipped"]:
        requires.insert(0, "Not yet in the To · What · Types · Phase shape, so not read: " + ", ".join(parts.pop("requires-skipped")) + ".")
    parts["requires"] = requires

    lines = ["| Term | Meaning | Owner |", "| --- | --- | --- |"]
    for short in sorted(expansions, key=str.lower):
        uses = collections.Counter({tab: len(re.findall(r"\b" + re.escape(short) + r"\b", t)) for tab, t in texts.items()})
        owner = uses.most_common(1)[0][0]
        lines.append(f"| {short} | {expansions[short][1]} | {owner} |")
    parts["glossary"] = ["\n".join(lines)]

    OUT.mkdir(parents=True, exist_ok=True)
    for name, chunks in parts.items():
        (OUT / f"{name}.md").write_text("\n\n".join(chunks) + "\n")
        print(f"docs/build/extracts/{name}.md")


if __name__ == "__main__":
    main()
