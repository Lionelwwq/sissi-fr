# -*- coding: utf-8 -*-
"""Attach prose audio to blocks, and find every French word that still has no clip."""
import hashlib, json, os, re, sys, collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pick_voice import split_sentences, keep            # reuse the exact same filter

C = json.load(open(os.path.join(HERE, "data", "content.json"), encoding="utf-8"))
WIDX = json.load(open(os.path.join(HERE, "data", "word_index.json"), encoding="utf-8"))

TAG = re.compile(r"<[^>]+>")
CJK = re.compile(r"[\u4e00-\u9fff]")
FR = re.compile(r"[A-Za-zÀ-ÿ]")
MAN = {}


def aid(text):
    t = re.sub(r"\s+", " ", text).strip()
    h = hashlib.md5(("V|" + t).encode("utf-8")).hexdigest()[:16]
    MAN[h] = {"text": t, "slow": False}
    return h


def french_bits(t):
    t = TAG.sub(" ", t or "")
    out = []
    for m in re.finditer(r"[«“\"]\s*([^»”\"]{8,200})\s*[»”\"]", t):
        s = m.group(1).strip()
        if len(FR.findall(s)) >= 8 and not CJK.search(s):
            out.append(s)
    for run in re.split(r"[\u4e00-\u9fff，。；：？！、（）【】]+", t):
        run = run.strip(" .,;:—-–·/|")
        if len(run) >= 14 and len(FR.findall(run)) >= 10 and not CJK.search(run):
            out.append(run)
    return out


def sentences_of(text):
    out, seen = [], set()
    for frag in french_bits(text):
        for part in split_sentences(frag):
            k = keep(part)
            if k and k.lower() not in seen:
                seen.add(k.lower())
                out.append(k)
    return out


voiced_blocks = 0
total_sent = 0
for ch in C["chapters"]:
    for b in ch["blocks"]:
        texts = []
        k = b["kind"]
        if k in ("para", "tip", "warn"):
            texts = [b.get("text", "")]
        elif k in ("bullets", "steps"):
            texts = b.get("items", [])
        elif k == "cards":
            texts = [c.get("note", "") for c in b.get("cards", [])]
        elif k == "model":
            texts = (b.get("model") or {}).get("notes", [])
        elif k == "table":
            aids = b.get("aids") or []
            texts = []
            for ri, row in enumerate(b.get("rows", [])):
                arow = aids[ri] if ri < len(aids) else []
                for ci, cell in enumerate(row):
                    if ci < len(arow) and arow[ci]:
                        continue
                    texts.append(cell)
        if not texts:
            continue
        sents, seen = [], set()
        for t in texts:
            for s in sentences_of(t):
                if s.lower() in seen:
                    continue
                seen.add(s.lower())
                sents.append(s)
        if sents:
            b["voice"] = [{"fr": s, "aid": aid(s)} for s in sents]
            voiced_blocks += 1
            total_sent += len(sents)

# ---- every French word form in the book that has no clip yet ----
def all_text(o, bag):
    if isinstance(o, dict):
        for v in o.values():
            all_text(v, bag)
    elif isinstance(o, list):
        for v in o:
            all_text(v, bag)
    elif isinstance(o, str):
        bag.append(o)

bag = []
all_text(C, bag)
forms = collections.Counter()
for t in bag:
    t = TAG.sub(" ", t)
    for w in re.findall(r"[A-Za-zÀ-ÿ]+(?:['’][A-Za-zÀ-ÿ]+)?", t):
        if len(w) >= 2:
            forms[w.lower().replace("’", "'")] += 1

missing = [w for w in forms if w not in WIDX]
print("blocks given prose audio: %d   sentences: %d" % (voiced_blocks, total_sent))
print("distinct word forms in book: %d   already voiced: %d   missing: %d"
      % (len(forms), len(forms) - len(missing), len(missing)))

json.dump(MAN, open(os.path.join(HERE, "tts_prose.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(sorted(missing), open(os.path.join(HERE, "words_missing.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(C, open(os.path.join(HERE, "data", "content.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("prose clips:", len(MAN))
