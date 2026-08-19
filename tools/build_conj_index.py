# -*- coding: utf-8 -*-
"""Reverse index: any conjugated word -> which verb / tense it belongs to.

Clicking « serions » in the book should say "être, conditionnel présent" instead of
sending her to guess the infinitive, which is the single hardest step for a learner.
"""
import json, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REF = json.load(open(os.path.join(HERE, "conj_ref.json"), encoding="utf-8"))

TFR = {
    "Present": "Présent",
    "PasseCompose": "Passé composé",
    "Imparfait": "Imparfait",
    "FuturSimple": "Futur simple",
    "Conditionnel": "Conditionnel présent",
    "Subjonctif": "Subjonctif présent",
}
PERSON_FR = ["je", "tu", "il / elle", "nous", "vous", "ils / elles"]
# words that are never the verb itself
SKIP = {"que", "qu", "je", "j", "tu", "il", "elle", "nous", "vous", "ils", "elles", "on"}
AUX = {"suis", "es", "est", "sommes", "êtes", "sont", "ai", "as", "a", "avons", "avez", "ont"}


def words(s):
    s = s.split(" / ")[0]                       # "il est allé / elle est allée"
    s = re.sub(r"\([^)]*\)", "", s)             # "allé(e)s" -> "allés"? no: -> "allés" handled below
    return [w for w in re.findall(r"[A-Za-zÀ-ÿ]+", s)]


def main():
    idx = {}

    def add(word, verb, tense, person, full, role):
        w = word.lower()
        if len(w) < 2 or w in SKIP:
            return
        bucket = idx.setdefault(w, [])
        for e in bucket:
            if e["v"] == verb and e["t"] == tense and e["role"] == role:
                if person and person not in e["p"]:
                    e["p"].append(person)
                return
        bucket.append({"v": verb, "t": tense, "p": [person] if person else [],
                       "ex": full, "role": role})

    for key, tb in REF["verbs"].items():
        inf = tb["inf"]
        for t in REF["tenses"]:
            for i, form in enumerate(tb[t]):
                ws = words(form)
                person = PERSON_FR[i]
                if not ws:
                    continue
                tail = [w for w in ws if w.lower() not in SKIP]
                if t == "PasseCompose" and len(tail) >= 2:
                    # auxiliary is already indexed under être/avoir; the participle identifies the verb
                    add(tail[-1], inf, TFR[t], None, form, "participe")
                    continue
                for w in tail:
                    if w.lower() in AUX and inf not in ("être", "avoir"):
                        continue
                    add(w, inf, TFR[t], person, form, "forme")
        # the infinitive itself; the past participle is already indexed off the
        # passé composé cell, so adding it again would show the same line twice
        add(inf, inf, "infinitif", None, inf, "infinitif")

    out = os.path.join(HERE, "data", "conj_index.json")
    json.dump(idx, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("keys:", len(idx))
    for probe in ("serions", "été", "aille", "irai", "faisons", "dû", "prennent", "veuille"):
        print(" ", probe, "->", json.dumps(idx.get(probe.lower()), ensure_ascii=False))


if __name__ == "__main__":
    main()
