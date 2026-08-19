# -*- coding: utf-8 -*-
"""Synthesize the theme clips and fold them into conj.zip (the mp3 pack)."""
import asyncio, json, os, sys, zipfile

import edge_tts

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "conj_parts2")          # same pool as the conjugation clips
VOICE = "fr-CA-SylvieNeural"
CONC = 6
FRAME, FRAME_SEC = 144, 576 / 24000.0
HEAD_PAD, TAIL_PAD = 0.05, 0.18

MAN = json.load(open(os.path.join(HERE, "tts_themes.json"), encoding="utf-8"))
print("theme clips:", len(MAN))

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
                if len(buf) < 500:
                    raise RuntimeError("empty")
                with open(p + ".part", "wb") as f:
                    f.write(trim(bytes(buf), first, last))
                os.replace(p + ".part", p)
                return
            except Exception as e:
                if attempt == 3:
                    fails.append((cid, item["text"][:50], repr(e)[:90]))
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
if missing:
    raise SystemExit("missing %d clips, not packing" % len(missing))

# rebuild conj.zip so it holds conjugation + theme clips together
old = json.load(open(os.path.join(HERE, "tts_manifest_all.json"), encoding="utf-8"))
allman = dict(old)
allman.update(MAN)
json.dump(allman, open(os.path.join(HERE, "tts_manifest_all.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

zp = os.path.join(HERE, "data", "conj.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
    for k in sorted(allman):
        z.write(os.path.join(OUT, k + ".mp3"), k + ".mp3")
print("conj.zip: %.2f MB, %d members" % (os.path.getsize(zp) / 1e6, len(allman)))
