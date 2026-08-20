# -*- coding: utf-8 -*-
"""Four dialogue lines carry aid:"" and are therefore silent taps.

33 items in content.json have an empty aid. 29 of them are correct: 14 grammar
patterns that contain Chinese (「il y a + 时段 + passé composé」), 15 「…」 placeholders
marking where she is meant to speak, and 2 「Sissi」 name slots. The other four are
real French she would tap expecting a voice — checked, no clip exists for those texts
anywhere in the three packs, so this is a gap and not a de-duplication.
"""
import asyncio, hashlib, io, json, os, re, sys

import edge_tts

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIP = os.path.join(ROOT, "clip")
CONTENT = os.path.join(ROOT, "data", "content.json")

FEMALE, MALE = "fr-CA-SylvieNeural", "fr-CA-ThierryNeural"
FRAME, FRAME_SEC = 144, 576 / 24000.0
HEAD_PAD, TAIL_PAD = 0.05, 0.18

D = json.load(io.open(CONTENT, encoding="utf-8"))

# find every dict that has an empty aid and speakable French next to it
targets = []


def walk(o, voice):
    if isinstance(o, dict):
        v = FEMALE if o.get("me") else (MALE if "me" in o else voice)
        if "aid" in o and not o["aid"]:
            t = (o.get("fr") or o.get("phrase") or o.get("say") or o.get("text") or "").strip()
            # speakable = has letters and no Chinese (the grammar patterns and 「…」 are not)
            if re.search(r"[A-Za-zÀ-ÿ]", t) and not re.search(r"[一-鿿]", t) and t not in ("Sissi",):
                targets.append((o, t, v))
        for val in o.values():
            walk(val, v)
    elif isinstance(o, list):
        for val in o:
            walk(val, voice)


walk(D, FEMALE)
print("silent lines found:", len(targets))
for _, t, v in targets:
    print("   %-14r %s" % (t, v.split("-")[-1]))
assert 1 <= len(targets) <= 8, "unexpected number of targets — look before synthesising"

have = set(x[:-4] for x in os.listdir(CLIP) if x.endswith(".mp3"))
jobs = []
for obj, text, voice in targets:
    cid = hashlib.md5((text + "|" + voice).encode("utf-8")).hexdigest()[:16]
    assert cid not in have or True
    obj["aid"] = cid
    if cid not in have:
        jobs.append((cid, text, voice))

print("to synthesize:", len(jobs))


def trim(data, first, last):
    if first is None or last is None or len(data) < FRAME * 6:
        return data
    n = len(data) // FRAME
    s = max(0, int((first / 1e7 - HEAD_PAD) / FRAME_SEC))
    e = min(n, int((last / 1e7 + TAIL_PAD) / FRAME_SEC) + 1)
    return data if e - s < 6 else data[s * FRAME:e * FRAME]


async def one(cid, text, voice):
    for attempt in range(5):
        try:
            c = edge_tts.Communicate(text, voice, boundary="WordBoundary")
            buf = bytearray()
            first = last = None
            async for ch in c.stream():
                if ch["type"] == "audio":
                    buf += ch["data"]
                elif ch["type"] == "WordBoundary":
                    if first is None:
                        first = ch["offset"]
                    last = ch["offset"] + ch["duration"]
            if len(buf) < 400:
                raise RuntimeError("empty")
            p = os.path.join(CLIP, cid + ".mp3")
            with open(p + ".part", "wb") as f:
                f.write(trim(bytes(buf), first, last))
            os.replace(p + ".part", p)
            print("   ok %s  %r" % (cid, text))
            return True
        except Exception as e:
            if attempt == 4:
                print("   FAILED %s %r %r" % (cid, text, e))
                return False
            await asyncio.sleep(1.5 * (attempt + 1))


async def main():
    return await asyncio.gather(*[one(*j) for j in jobs])


results = asyncio.run(main()) if jobs else []
assert all(results), "some clips failed — content.json not written"

io.open(CONTENT, "w", encoding="utf-8", newline="\n").write(
    json.dumps(D, ensure_ascii=False, separators=(",", ":")))
print("content.json updated; clip/ now holds",
      len([x for x in os.listdir(CLIP) if x.endswith('.mp3')]), "mp3")
