# -*- coding: utf-8 -*-
"""Re-synthesize the 8216 opus clips as mp3.

Ogg Opus only plays in Safari from iOS 17.4 on, so on an older iPhone a third of
the book is silent with no explanation. edge-tts emits mp3 natively; the padding
it adds is cut by slicing whole CBR frames (144 bytes = 24 ms) between the first
and last WordBoundary — the same trick the newer packs use, since ffmpeg is gone.
Resumable: anything already written is skipped.
"""
import asyncio, io, json, os, sys

import edge_tts

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CONC = 10
FRAME, FRAME_SEC = 144, 576 / 24000.0
HEAD_PAD, TAIL_PAD = 0.05, 0.18

os.makedirs(OUT, exist_ok=True)
MAN = json.load(io.open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
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
        for attempt in range(5):
            try:
                c = edge_tts.Communicate(item["text"], item["voice"], boundary="WordBoundary")
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
                if attempt == 4:
                    fails.append((cid, item["text"][:60], repr(e)[:90]))
                else:
                    await asyncio.sleep(1.5 * (attempt + 1))


async def main():
    sem = asyncio.Semaphore(CONC)
    todo = [(k, v) for k, v in MAN.items() if not os.path.exists(os.path.join(OUT, k + ".mp3"))]
    print("to synthesize:", len(todo), "of", len(MAN), flush=True)
    done = 0
    for i in range(0, len(todo), 200):
        await asyncio.gather(*[one(sem, k, v) for k, v in todo[i:i + 200]])
        done += len(todo[i:i + 200])
        print("  %d/%d  (failures so far: %d)" % (done, len(todo), len(fails)), flush=True)


asyncio.run(main())
print("failures:", len(fails))
for f in fails[:12]:
    print("  ", f)
missing = [k for k in MAN if not os.path.exists(os.path.join(OUT, k + ".mp3"))]
print("missing after run:", len(missing))
json.dump(missing, io.open(os.path.join(HERE, "missing.json"), "w", encoding="utf-8"))
