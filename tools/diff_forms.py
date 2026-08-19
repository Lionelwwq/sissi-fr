# -*- coding: utf-8 -*-
"""Diff my hand-written table against the 9 agents that never saw it."""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = json.load(open(os.path.join(HERE, "conj_check.json"), encoding="utf-8"))
TENSES = ["Present", "PasseCompose", "Imparfait", "FuturSimple", "Conditionnel", "Subjonctif"]
PERSONS = ["je", "tu", "il", "nous", "vous", "ils"]


def norm(s):
    s = (s or "").lower().replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


bad, missing, total = [], [], 0
for v, mine in CHECK.items():
    p = os.path.join(HERE, "gen", "forms_%s.json" % v)
    if not os.path.exists(p):
        missing.append(v)
        continue
    got = json.load(open(p, encoding="utf-8"))
    for t in TENSES:
        rows = got.get(t) or []
        for i in range(6):
            total += 1
            a = mine[t][i]
            b = rows[i] if i < len(rows) else None
            if norm(a) != norm(b):
                bad.append((v, t, PERSONS[i], a, b))

print("files missing:", missing or "none")
print("cells compared:", total)
print("disagreements:", len(bad))
for v, t, p, a, b in bad:
    print("  %-8s %-13s %-5s  mine=%-28r agent=%r" % (v, t, p, a, b))
