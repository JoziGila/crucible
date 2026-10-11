#!/usr/bin/env python3
"""Collect decisions, contract change requests, interfaces and open questions from every tab.

    python3 docs/tools/extract.py        writes docs/build/extracts/{decisions,ccr,interfaces,open-questions}.md

Use it for the ruling step, the consistency pass and the Decisions log.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC, OUT = ROOT / "spec", ROOT / "build" / "extracts"
DECISION = re.compile(r"^(?:\s*(?:[-*+]|\d+\.)\s+)?(\*\*Decision D-[A-Z]{3}-\d+:\*\*.*)$", re.M)


def section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.M)
    return (rest[: n.start()] if n else rest).strip()


def main():
    parts = {"decisions": [], "ccr": [], "interfaces": [], "open-questions": []}
    for f in sorted(SPEC.glob("[0-9][0-9]-*.md")):
        if not "01" <= f.name[:2] <= "12":
            continue
        t = f.read_text()
        decisions = DECISION.findall(t)
        parts["decisions"].append(f"### {f.name} ({len(decisions)} decisions)\n\n" + "\n\n".join(decisions))
        parts["ccr"].append(f"### {f.name}\n\n" + section(t, "Contract change requests"))
        parts["interfaces"].append(f"### {f.name}\n\n" + section(t, "Interfaces with other subsystems"))
        parts["open-questions"].append(f"### {f.name}\n\n" + section(t, "Open questions"))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, chunks in parts.items():
        (OUT / f"{name}.md").write_text("\n\n".join(chunks) + "\n")
        print(f"docs/build/extracts/{name}.md")


if __name__ == "__main__":
    main()
