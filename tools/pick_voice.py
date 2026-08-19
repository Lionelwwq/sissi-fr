# -*- coding: utf-8 -*-
"""Split the unvoiced French into single sentences and keep only what is worth hearing.

The raw fragments often glue a wrong example to its correction («❌ … ✅ …»); reading
that aloud would teach the mistake, so the ❌ side is dropped, not just marked.
"""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
frags = json.load(open(os.path.join(HERE, "unvoiced.json"), encoding="utf-8"))

FR_WORDS = set("""le la les un une des du de d au aux je tu il elle on nous vous ils elles
me te se ce cet cette ces mon ma mes ton ta tes son sa ses notre votre leur leurs
est sont suis es sommes êtes ai as avons avez ont était étais avait avaient sera serait
que qui quoi dont où pour dans avec sans sous sur chez vers par pas ne plus moins très
et ou mais donc car si comme quand parce bien tout tous toute toutes autre même
faire fais fait aller vais va allons vouloir veux veut pouvoir peux peut devoir dois doit
c'est j'ai qu'il qu'elle d'un d'une l'on y a n'est""".split())
ENGLISH = set("""the and with for you your this that from have has are was were will would
entry express score points immigration federal program rounds invitations""".split())

BAD = re.compile(r"[❌✗×]")
GOOD = re.compile(r"[✅✓]")
JUNK = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩→←↔＝=<>\[\]{}]|https?://")


def split_sentences(t):
    # a wrong/right pair: keep only what follows the ✅
    if GOOD.search(t) and BAD.search(t):
        t = GOOD.split(t, 1)[1]
    elif BAD.search(t) and not GOOD.search(t):
        return []                                  # wrong example with no correction
    t = GOOD.sub(" ", t)
    parts = re.split(r"(?<=[.!?…])\s+|\s+/\s+|\s*\|\s*|\s*；\s*", t)
    return [p.strip(" .,;:/|—-–·«»\"'") for p in parts]


def words(s):
    return re.findall(r"[A-Za-zÀ-ÿ']+", s.lower())


def keep(s):
    if not (10 <= len(s) <= 170) or JUNK.search(s):
        return None
    w = words(s)
    if not (3 <= len(w) <= 32):
        return None
    fr = sum(1 for x in w if x in FR_WORDS)
    en = sum(1 for x in w if x in ENGLISH)
    acc = len(re.findall(r"[àâäçéèêëîïôöùûüÿœÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒ]", s))
    if en > fr or (fr == 0 and acc == 0) or fr < 1:
        return None
    return re.sub(r"\s+", " ", s)


picked, seen = [], set()
for f in frags:
    for part in split_sentences(f):
        k = keep(part)
        if not k:
            continue
        low = k.lower()
        if low in seen:
            continue
        seen.add(low)
        picked.append(k)

chars = sum(len(x) for x in picked)
print("sentences kept: %d" % len(picked))
print("characters: %d  (~%.0f min of speech, ~%.0f MB mp3)" % (chars, chars / 14.0 / 60, chars / 14.0 * 6 / 1000))
print()
for s in picked[:14]:
    print("   ", s[:92])
json.dump(picked, open(os.path.join(HERE, "voice_pick.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
