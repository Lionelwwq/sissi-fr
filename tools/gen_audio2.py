# -*- coding: utf-8 -*-
"""Re-synthesize every new clip and trim the silence at MP3 frame level.

edge-tts pads short utterances out to a fixed ~1.78 s envelope — every single-word
clip came back at exactly 10656 bytes, mostly silence. ffmpeg used to cut that; with
ffmpeg gone, the WordBoundary events give exact speech start/end and the stream is
CBR (144-byte frames, 24 ms each), so whole frames can be sliced without decoding.
"""
import asyncio, hashlib, json, os, sys, zipfile

import edge_tts

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "conj_parts2")
VOICE = "fr-CA-SylvieNeural"
CONC = 6
FRAME = 144
FRAME_SEC = 576 / 24000.0
HEAD_PAD, TAIL_PAD = 0.05, 0.18      # keep the attack and the final release

os.makedirs(OUT, exist_ok=True)

MAN = json.load(open(os.path.join(HERE, "tts_manifest.json"), encoding="utf-8"))
CONJ = json.load(open(os.path.join(HERE, "data", "conj_index.json"), encoding="utf-8"))
WIDX = json.load(open(os.path.join(HERE, "data", "word_index.json"), encoding="utf-8"))

NEW_WORDS = {}
for w in CONJ:
    if w in WIDX:
        continue                      # already recorded in the 3000-word pack
    wid = "c" + hashlib.md5(("W|" + w).encode("utf-8")).hexdigest()[:11]
    NEW_WORDS[w] = wid
    MAN[wid] = {"text": w, "slow": False}

json.dump(MAN, open(os.path.join(HERE, "tts_manifest_all.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("clips:", len(MAN), "(single words:", len(NEW_WORDS), ")")


def trim(data, first, last):
    if first is None or last is None or len(data) < FRAME * 6:
        return data
    n = len(data) // FRAME
    s = max(0, int((first / 1e7 - HEAD_PAD) / FRAME_SEC))
    e = min(n, int((last / 1e7 + TAIL_PAD) / FRAME_SEC) + 1)
    if e - s < 6:
        return data
    return data[s * FRAME:e * FRAME]


fails = []


async def one(sem, cid, item):
    async with sem:
        path = os.path.join(OUT, cid + ".mp3")
        if os.path.exists(path):
            return
        rate = "-12%" if item["slow"] else "+0%"
        for attempt in range(4):
            try:
                # SentenceBoundary (the default) reports the padded envelope, not the
                # speech; only WordBoundary is tight enough to cut against
                c = edge_tts.Communicate(item["text"], VOICE, rate=rate,
                                         boundary="WordBoundary")
                buf = bytearray()
                first = last = None
                async for ch in c.stream():
                    if ch["type"] == "audio":
                        buf += ch["data"]
                    elif ch["type"] == "WordBoundary":
                        if first is None:
                            first = ch["offset"]
                        last = ch["offset"] + ch["duration"]
                if len(buf) < 500:
                    raise RuntimeError("empty audio")
                out = trim(bytes(buf), first, last)
                with open(path + ".part", "wb") as f:
                    f.write(out)
                os.replace(path + ".part", path)
                return
            except Exception as e:
                if attempt == 3:
                    fails.append((cid, item["text"], repr(e)[:110]))
                else:
                    await asyncio.sleep(1.5 * (attempt + 1))


async def main():
    sem = asyncio.Semaphore(CONC)
    todo = [(k, v) for k, v in MAN.items() if not os.path.exists(os.path.join(OUT, k + ".mp3"))]
    print("to synthesize:", len(todo))
    done = 0
    for i in range(0, len(todo), 60):
        await asyncio.gather(*[one(sem, k, v) for k, v in todo[i:i + 60]])
        done += len(todo[i:i + 60])
        print("  %d/%d" % (done, len(todo)), flush=True)


asyncio.run(main())
print("failures:", len(fails))
for f in fails[:8]:
    print("  ", f)

missing = [k for k in MAN if not os.path.exists(os.path.join(OUT, k + ".mp3"))]
print("missing:", len(missing))
if missing:
    raise SystemExit("not packing")

old = sum(os.path.getsize(os.path.join(HERE, "conj_parts", k + ".mp3")) for k in MAN
          if os.path.exists(os.path.join(HERE, "conj_parts", k + ".mp3")))
new = sum(os.path.getsize(os.path.join(OUT, k + ".mp3")) for k in MAN)
print("bytes before trim: %.2f MB  after: %.2f MB" % (old / 1e6, new / 1e6))

wordsz = [os.path.getsize(os.path.join(OUT, i + ".mp3")) for i in NEW_WORDS.values()]
print("single-word clips: avg %d bytes, min %d, max %d" %
      (sum(wordsz) / len(wordsz), min(wordsz), max(wordsz)))

zp = os.path.join(HERE, "data", "conj.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
    for k in sorted(MAN):
        z.write(os.path.join(OUT, k + ".mp3"), k + ".mp3")
print("conj.zip: %.2f MB, %d members" % (os.path.getsize(zp) / 1e6, len(MAN)))

WIDX.update(NEW_WORDS)
json.dump(WIDX, open(os.path.join(HERE, "data", "word_index.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print("word_index entries:", len(WIDX))
