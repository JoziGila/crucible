#!/usr/bin/env python3
"""Parse the adversarial review reports (docs/review/R*.md) into docs/review/findings.json.

    python3 docs/tools/findings.py       rewrites docs/review/findings.json and prints counts by severity and tab

Each finding starts with a heading: ### R<n>-<nn> · <Critical|Major|Minor> · Targets: <TAB>, <TAB>
"""
import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review"
HEAD = re.compile(r"^### (R\d-\d+) · (Critical|Major|Minor) · Targets: (.*)$", re.M)


def main():
    out = []
    for f in sorted(REVIEW.glob("R[0-9]-*.md")):
        t = f.read_text()
        heads = list(HEAD.finditer(t))
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
            targets = [x.strip().upper() for x in re.split(r"[,;/]| and ", m.group(3)) if x.strip()]
            out.append({"id": m.group(1), "sev": m.group(2), "targets": targets, "body": t[m.end():end].strip(), "file": f.name})
    (REVIEW / "findings.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(len(out), "findings", dict(collections.Counter(x["sev"] for x in out)))
    by_tab = collections.Counter(t for x in out for t in x["targets"])
    print(", ".join(f"{k} {v}" for k, v in sorted(by_tab.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
