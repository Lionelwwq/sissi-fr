# -*- coding: utf-8 -*-
"""Validate the 9 teaching files before they become book chapters."""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
REF = json.load(open(os.path.join(HERE, "conj_ref.json"), encoding="utf-8"))
TENSES_FR = ["Présent", "Passé composé", "Imparfait", "Futur simple",
             "Conditionnel présent", "Subjonctif présent"]

# she is female: an adjective or participle about herself must carry the -e
MASC = re.compile(
    r"\bje (?:suis|serais|serai|étais|me sens|me suis)\s+(?:tr[eè]s\s+|d[ée]j[àa]\s+|toujours\s+)?"
    r"(n[ée]|all[ée]|venu|arriv[ée]|rest[ée]|parti|entr[ée]|sorti|install[ée]|inscrit|"
    r"pr[êe]t|content|heureux|s[ûu]r|certain|convaincu|habitu[ée]|dipl[ôo]m[ée]|motiv[ée]|"
    r"disponible?|int[ée]ress[ée]|fatigu[ée]|occup[ée]|d[ée]sol[ée])\b",
    re.I)


def forms_of(vkey):
    tb = REF["verbs"][vkey]
    out = set()
    for t in REF["tenses"]:
        for cell in tb[t]:
            for w in re.findall(r"[A-Za-zÀ-ÿ]+", cell.split(" / ")[0]):
                if w.lower() not in ("je", "tu", "il", "elle", "nous", "vous", "ils",
                                     "elles", "que", "qu", "j"):
                    out.add(w.lower())
    out.add(tb["inf"].lower())
    return out


def has_verb(text, forms):
    ws = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]+", text or "")}
    return bool(ws & forms)


problems = []
for vkey in REF["verbs"]:
    p = os.path.join(HERE, "gen", "teach_%s.json" % vkey)
    d = json.load(open(p, encoding="utf-8"))
    forms = forms_of(vkey)

    for k in ("why", "tense_use", "traps", "pron", "chunks"):
        if not d.get(k):
            problems.append((vkey, "missing", k))

    tu = d.get("tense_use") or []
    if len(tu) != 6:
        problems.append((vkey, "tense_use count", len(tu)))
    for i, x in enumerate(tu):
        want = TENSES_FR[i] if i < 6 else "?"
        if x.get("tense", "").strip().lower() != want.lower():
            problems.append((vkey, "tense name", "%r != %r" % (x.get("tense"), want)))
        if not has_verb(x.get("example_fr"), forms):
            problems.append((vkey, "example lacks verb", x.get("example_fr")))

    for x in d.get("chunks") or []:
        if not has_verb(x.get("fr"), forms):
            problems.append((vkey, "chunk lacks verb", x.get("fr")))

    blob = json.dumps(d, ensure_ascii=False)
    for m in MASC.finditer(blob):
        problems.append((vkey, "masculine agreement", m.group(0)))

    for x in d.get("traps") or []:
        if (x.get("wrong") or "").strip() == (x.get("right") or "").strip():
            problems.append((vkey, "trap identical", x.get("wrong")))

n = {v: len(json.load(open(os.path.join(HERE, "gen", "teach_%s.json" % v), encoding="utf-8"))["chunks"])
     for v in REF["verbs"]}
print("chunks per verb:", n, "total", sum(n.values()))
print("problems:", len(problems))
for x in problems:
    print("  ", x)
