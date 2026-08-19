# -*- coding: utf-8 -*-
"""How much French in the book has no audio attached?"""
import json, os, re, sys, collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "data", "content.json"), encoding="utf-8"))

TAG = re.compile(r"<[^>]+>")
CJK = re.compile(r"[\u4e00-\u9fff]")
FR = re.compile(r"[A-Za-zÀ-ÿ]")


def strip(t):
    return TAG.sub(" ", t or "")


def french_bits(t):
    """French runs inside a mixed Chinese/French string, long enough to be worth a clip."""
    t = strip(t)
    out = []
    # « ... » quoted French is the book's own convention
    for m in re.finditer(r"[«“\"]\s*([^»”\"]{8,160})\s*[»”\"]", t):
        s = m.group(1).strip()
        if len(FR.findall(s)) >= 8 and not CJK.search(s):
            out.append(s)
    # otherwise: long Latin-only runs
    for run in re.split(r"[\u4e00-\u9fff，。；：？！、（）【】]+", t):
        run = run.strip(" .,;:—-–·/|")
        if len(run) >= 14 and len(FR.findall(run)) >= 10 and not CJK.search(run):
            out.append(run)
    seen, uniq = set(), []
    for s in out:
        k = s.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    return uniq


stats = collections.Counter()
samples = collections.defaultdict(list)
total_new = []

for ch in C["chapters"]:
    for b in ch["blocks"]:
        k = b["kind"]
        if k in ("para", "tip", "warn"):
            for s in french_bits(b.get("text", "")):
                stats[k] += 1; total_new.append(s)
                if len(samples[k]) < 3: samples[k].append(s)
        elif k in ("bullets", "steps"):
            for it in b.get("items", []):
                for s in french_bits(it):
                    stats[k] += 1; total_new.append(s)
                    if len(samples[k]) < 3: samples[k].append(s)
        elif k == "table":
            aids = b.get("aids") or []
            for ri, row in enumerate(b.get("rows", [])):
                for ci, cell in enumerate(row):
                    if (aids[ri] if ri < len(aids) else [None] * 9)[ci] if ri < len(aids) and ci < len(aids[ri]) else None:
                        continue
                    for s in french_bits(cell):
                        stats["table-cell"] += 1; total_new.append(s)
                        if len(samples["table-cell"]) < 3: samples["table-cell"].append(s)
        elif k == "cards":
            for c in b.get("cards", []):
                for s in french_bits(c.get("note", "")):
                    stats["card-note"] += 1; total_new.append(s)
                    if len(samples["card-note"]) < 3: samples["card-note"].append(s)
        elif k == "model":
            for n in (b.get("model") or {}).get("notes", []):
                for s in french_bits(n):
                    stats["model-note"] += 1; total_new.append(s)
                    if len(samples["model-note"]) < 3: samples["model-note"].append(s)

uniq = {s.lower(): s for s in total_new}
print("unvoiced French fragments by location:")
for k, n in stats.most_common():
    print("  %-12s %5d" % (k, n))
print("total %d, unique %d" % (sum(stats.values()), len(uniq)))
print()
for k, v in samples.items():
    print("---", k)
    for s in v: print("     ", s[:100])
json.dump(sorted(uniq.values()), open(os.path.join(HERE, "unvoiced.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
