# -*- coding: utf-8 -*-
"""Synthesize the new clips with edge-tts and pack them into conj.zip.

No ffmpeg in this environment any more, so these stay as edge-tts's native
48 kbps mp3 instead of the 18 kbps opus the older packs use. Removing the
question banks frees far more space than that costs.
"""
import asyncio, json, os, sys, zipfile

import edge_tts

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "conj_parts")
VOICE = "fr-CA-SylvieNeural"
CONC = 6

os.makedirs(OUT, exist_ok=True)
MAN = json.load(open(os.path.join(HERE, "tts_manifest.json"), encoding="utf-8"))

# single-word clips so any conjugated form in the book can be clicked and heard
CONJ = json.load(open(os.path.join(HERE, "data", "conj_index.json"), encoding="utf-8"))
WIDX = json.load(open(os.path.join(HERE, "data", "word_index.json"), encoding="utf-8"))
import hashlib
NEW_WORDS = {}
for w in CONJ:
    if w in WIDX:
        continue
    wid = "c" + hashlib.md5(("W|" + w).encode("utf-8")).hexdigest()[:11]
    NEW_WORDS[w] = wid
    MAN[wid] = {"text": w, "slow": False}

print("clips total:", len(MAN), "(new single words:", len(NEW_WORDS), ")")

todo = [(k, v) for k, v in MAN.items() if not os.path.exists(os.path.join(OUT, k + ".mp3"))]
print("to synthesize:", len(todo))

fails = []


async def one(sem, cid, item):
    async with sem:
        rate = "-12%" if item["slow"] else "+0%"
        path = os.path.join(OUT, cid + ".mp3")
        for attempt in range(4):
            try:
                c = edge_tts.Communicate(item["text"], VOICE, rate=rate)
                await c.save(path + ".part")
                if os.path.getsize(path + ".part") < 500:
                    raise RuntimeError("empty audio")
                os.replace(path + ".part", path)
                return
            except Exception as e:
                if attempt == 3:
                    fails.append((cid, item["text"], repr(e)[:120]))
                else:
                    await asyncio.sleep(1.5 * (attempt + 1))


async def main():
    sem = asyncio.Semaphore(CONC)
    tasks = [one(sem, k, v) for k, v in todo]
    done = 0
    for chunk in [tasks[i:i + 60] for i in range(0, len(tasks), 60)]:
        await asyncio.gather(*chunk)
        done += len(chunk)
        print("  %d/%d" % (done, len(tasks)), flush=True)


if todo:
    asyncio.run(main())

print("failures:", len(fails))
for f in fails[:10]:
    print("  ", f)

have = {f[:-4] for f in os.listdir(OUT) if f.endswith(".mp3")}
missing = [k for k in MAN if k not in have]
print("missing after run:", len(missing))

if not missing:
    zp = os.path.join(HERE, "data", "conj.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
        for k in sorted(MAN):
            z.write(os.path.join(OUT, k + ".mp3"), k + ".mp3")
    print("conj.zip:", round(os.path.getsize(zp) / 1e6, 2), "MB", len(MAN), "members")

    WIDX.update(NEW_WORDS)
    json.dump(WIDX, open(os.path.join(HERE, "data", "word_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print("word_index entries:", len(WIDX))
else:
    print("NOT packing: clips missing")
