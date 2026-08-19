# -*- coding: utf-8 -*-
"""Synthesize the prose sentences and the missing word clips."""
import asyncio, hashlib, json, os, sys, zipfile

import edge_tts

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "conj_parts2")
VOICE = "fr-CA-SylvieNeural"
CONC = 8
FRAME, FRAME_SEC = 144, 576 / 24000.0
HEAD_PAD, TAIL_PAD = 0.05, 0.18

os.makedirs(OUT, exist_ok=True)
MAN = json.load(open(os.path.join(HERE, "tts_prose.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(HERE, "words_missing.json"), encoding="utf-8"))

NEW_WORDS = {}
for w in WORDS:
    wid = "w" + hashlib.md5(("W2|" + w).encode("utf-8")).hexdigest()[:11]
    NEW_WORDS[w] = wid
    MAN[wid] = {"text": w, "slow": False}

json.dump(MAN, open(os.path.join(HERE, "tts_more_all.json"), "w", encoding="utf-8"), ensure_ascii=False)
json.dump(NEW_WORDS, open(os.path.join(HERE, "new_word_ids.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("clips to make: %d  (prose %d + words %d)" % (len(MAN), len(MAN) - len(NEW_WORDS), len(NEW_WORDS)))

fails = []


def trim(data, first, last):
    if first is None or last is None or len(data) < FRAME * 6:
        return data
    n = len(data) // FRAME
    s = max(0, int((first / 1e7 - HEAD_PAD) / FRAME_SEC))
    e = min(n, int((last / 1e7 + TAIL_PAD) / FRAME_SEC) + 1)
    return data if e - s < 6 else data[s * FRAME:e * FRAME]


async def one(sem, cid, item):
    async with sem:
        p = os.path.join(OUT, cid + ".mp3")
        if os.path.exists(p):
            return
        for attempt in range(4):
            try:
                c = edge_tts.Communicate(item["text"], VOICE, boundary="WordBoundary")
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
                with open(p + ".part", "wb") as f:
                    f.write(trim(bytes(buf), first, last))
                os.replace(p + ".part", p)
                return
            except Exception as e:
                if attempt == 3:
                    fails.append((cid, item["text"][:50], repr(e)[:80]))
                else:
                    await asyncio.sleep(1.5 * (attempt + 1))


async def main():
    sem = asyncio.Semaphore(CONC)
    todo = [(k, v) for k, v in MAN.items() if not os.path.exists(os.path.join(OUT, k + ".mp3"))]
    print("to synthesize:", len(todo), flush=True)
    done = 0
    for i in range(0, len(todo), 200):
        await asyncio.gather(*[one(sem, k, v) for k, v in todo[i:i + 200]])
        done += len(todo[i:i + 200])
        print("  %d/%d  (failures so far: %d)" % (done, len(todo), len(fails)), flush=True)


asyncio.run(main())
print("failures:", len(fails))
for f in fails[:10]:
    print("  ", f)
missing = [k for k in MAN if not os.path.exists(os.path.join(OUT, k + ".mp3"))]
print("missing after run:", len(missing))
