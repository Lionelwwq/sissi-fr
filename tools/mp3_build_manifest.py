# -*- coding: utf-8 -*-
"""Rebuild the text behind every .opus clip so it can be re-synthesized as mp3.

The opus packs predate the loss of ffmpeg and their manifest is gone; the text is
recovered from content.json (chapter audio) and word_index.json (single words).
Three shapes carry audio ids: `aid` next to the French, `aid_ex` next to
`example_fr`, and `aids` as a grid parallel to a table's `rows`. Clips nothing
references any more — leftovers from the deleted question banks — are listed
separately so they can simply be dropped.
"""
import html, io, json, os, re, sys, zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HERE = os.path.dirname(os.path.abspath(__file__))

MALE = "fr-CA-ThierryNeural"      # 考官
FEMALE = "fr-CA-SylvieNeural"     # 考生 / 默认
TAG = re.compile(r"<[^>]+>")
FR = re.compile(r"[A-Za-zÀ-ÿ]")


def spoken(s):
    s = html.unescape(TAG.sub(" ", str(s or "")))
    return re.sub(r"\s+", " ", s).strip()


C = json.load(io.open(os.path.join(DATA, "content.json"), encoding="utf-8"))
texts = {}


def put(aid, raw, voice):
    if not aid:
        return
    t = spoken(raw)
    if t and FR.search(t):
        texts[aid] = {"text": t, "voice": voice}


def walk(o, voice):
    if isinstance(o, dict):
        v = FEMALE if o.get("me") else (MALE if "me" in o else voice)
        put(o.get("aid"), o.get("fr") or o.get("phrase") or o.get("say") or o.get("text"), v)
        put(o.get("aid_ex"), o.get("example_fr"), v)
        rows, grid = o.get("rows"), o.get("aids")
        if isinstance(rows, list) and isinstance(grid, list):
            for ri, row in enumerate(rows):
                for ci, cell in enumerate(row or []):
                    put((grid[ri] or [])[ci] if ri < len(grid) and grid[ri] else None, cell, v)
        for val in o.values():
            walk(val, v)
    elif isinstance(o, list):
        for val in o:
            walk(val, voice)


walk(C, FEMALE)

WI = json.load(io.open(os.path.join(DATA, "word_index.json"), encoding="utf-8"))
byid = {}
for w, i in WI.items():
    byid.setdefault(i, w)

man, orphans = {}, {}
for zname in ("audio.zip", "words.zip"):
    with zipfile.ZipFile(os.path.join(DATA, zname)) as z:
        for name in z.namelist():
            base, ext = name.rsplit(".", 1)
            if ext != "opus":
                continue
            if base in texts:
                man[base] = dict(texts[base], zip=zname)
            elif base in byid:
                man[base] = {"text": byid[base], "voice": FEMALE, "zip": zname}
            else:
                orphans.setdefault(zname, []).append(base)

json.dump(man, io.open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False)
json.dump(orphans, io.open(os.path.join(HERE, "orphans.json"), "w", encoding="utf-8"), ensure_ascii=False)

nm = sum(1 for v in man.values() if v["voice"] == MALE)
print("to synthesize:", len(man), " (male %d / female %d)" % (nm, len(man) - nm))
for k, v in orphans.items():
    print("orphan clips in", k, len(v))
lens = sorted(len(v["text"]) for v in man.values())
print("text length  min %d  median %d  max %d" % (lens[0], lens[len(lens) // 2], lens[-1]))
