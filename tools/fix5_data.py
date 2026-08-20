# -*- coding: utf-8 -*-
"""Content and dictionary corrections.

data/ is the source of truth now (the scratchpad that once held bank_dict.json gets
wiped), so these edit the repo's own files in place. Every change prints a count.

Careful with the dictionary: French really does put a space before ; : ! ? — that is
the rule 第 12 章 teaches — and « » … ’ — are French punctuation, not damage. Only the
full-width CJK forms left behind when the bilingual source was split are stray."""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load(n):
    return json.load(io.open(os.path.join(DATA, n), encoding="utf-8"))


def dump(n, o):
    io.open(os.path.join(DATA, n), "w", encoding="utf-8", newline="\n").write(
        json.dumps(o, ensure_ascii=False, separators=(",", ":")))


# ---------------------------------------------------------------- 1. cross-references
# Two chapters were inserted at some point and these four pointers never moved. The
# ten-topic argument bank is 第 55-56 章; 第 53-54 章 is 万能理由 / 万能句型.
D = load("content.json")
chs = {c["no"]: c["zh"] for c in D["chapters"]}
assert "论点库" in chs[55] and "论点库" in chs[56], "chapter 55/56 are not the topic bank any more"
assert "论点库" not in chs[53] and "论点库" not in chs[54], "53/54 look like the topic bank now"

blob = json.dumps(D, ensure_ascii=False)
n = len(re.findall(r"第\s*53\s*-\s*54\s*章", blob))
blob = re.sub(r"第(\s*)53(\s*)-(\s*)54(\s*)章", r"第\g<1>55\g<2>-\g<3>56\g<4>章", blob)
assert "第 53-54 章" not in blob and "第53-54章" not in blob
dump("content.json", json.loads(blob))
print("content.json: repointed %d references from 第 53-54 章 to 第 55-56 章" % n)

# ---------------------------------------------------------------- 2. dictionary examples
dic = load("dict.json")

STRAY = "，。、；：！？【】〖〗～"          # full-width leftovers, no French use
WIDE = {"（": "(", "）": ")", "／": "/", "　": " "}
junk = cutfix = 0
before = {}


def tidy(s):
    for a, b in WIDE.items():
        s = s.replace(a, b)
    s = re.sub("[" + re.escape(STRAY) + "]", " ", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"[ \t]+", " ", s).strip()
    s = s.strip("/,;·-– ")
    return re.sub(r"[ \t]+", " ", s).strip()


for k, v in dic.items():
    ex = v.get("ex")
    if not isinstance(ex, str) or not ex.strip():
        continue
    orig = ex

    # 163 examples were hard-cut at exactly 120 characters; 135 stop mid-word with
    # nothing to say so. Trim back to the last whole word and end with an ellipsis.
    if len(ex) == 120 and re.search(r"[A-Za-zÀ-ÿ]$", ex):
        head = ex.rsplit(" ", 1)[0].rstrip(" ,;:")
        if len(head) > 40:
            ex = head + "…"
            cutfix += 1

    # 317 entries carry punctuation stranded when the Chinese half was deleted:
    # 「； parce que / car」, 「falloir il faut， je。」, 「Salut ! Ça va ?（ ）」.
    if re.search("[" + re.escape(STRAY) + "]|[（）／]", ex):
        ex = tidy(ex)
        junk += 1

    if ex != orig:
        before[k] = orig
        if len(re.findall(r"[A-Za-zÀ-ÿ]", ex)) < 3:
            v.pop("ex", None)
        else:
            v["ex"] = ex

print("dict.json: tidied %d stranded-punctuation examples, ended %d mid-word cuts"
      % (junk, cutfix))
print("           entries changed: %d of %d" % (len(before), len(dic)))
for k in list(before)[:8]:
    print("   %-14s %r\n   %-14s -> %r" % (k, before[k][:80], "", dic[k].get("ex", "(dropped)")[:80]))
dump("dict.json", dic)

left = [k for k, v in dic.items()
        if isinstance(v.get("ex"), str) and re.search("[" + re.escape(STRAY) + "]|[（）／]", v["ex"])]
assert not left, ("stray punctuation survived", left[:5])
print("           no stray full-width punctuation left")
