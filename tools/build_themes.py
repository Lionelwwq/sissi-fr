# -*- coding: utf-8 -*-
"""Turn the 10 theme files into two Part VIII chapters + a TTS manifest.

She asked for plain language, so the check pass below is not cosmetic: anything that
slipped past the agents gets reported before it reaches the book.
"""
import hashlib, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "gen2")
COLOR = "#7e22ce"          # Part VIII
CIRC = "①②③④⑤⑥⑦⑧⑨⑩"

THEMES = [
    ("travail", "工作"), ("education", "教育"), ("technologie", "科技"),
    ("sante", "健康"), ("environnement", "环境"), ("famille", "家庭"),
    ("ville", "城市生活"), ("consommation", "消费"), ("voyage", "旅游"),
    ("societe", "社会"),
]

# things she explicitly does not want to see
BANNED = [
    (r"\bdont\b", "关系代词 dont"),
    (r"\blequel|laquelle|auquel|duquel\b", "关系代词 lequel 类"),
    (r"\bnéanmoins\b", "书面连接词 néanmoins"),
    (r"\btoutefois\b", "书面连接词 toutefois"),
    (r"\ben outre\b", "书面连接词 en outre"),
    (r"\bcependant\b", "书面连接词 cependant"),
    (r"\bdans la mesure où\b", "书面结构"),
    (r"\bforce est de\b", "书面结构"),
    (r"\bil n'en demeure\b", "书面结构"),
    (r"\baccro[îi]tre|engendrer|pallier|pr[ôo]ner|s'av[ée]rer\b", "书面动词"),
    (r"\bind[ée]niable|pr[ée]pond[ée]rant|not(?:oire|amment) accru\b", "书面形容词"),
    (r"\bqu[e']\s+\w+\s+(?:soit|ait|puisse|fasse|aille|vienne|prenne)\b", "虚拟式"),
    (r"\bil faut que\b", "il faut que + 虚拟式"),
]
MAXWORDS = 18

MANIFEST = {}


def aid(text):
    t = re.sub(r"\s+", " ", text).strip()
    h = hashlib.md5(("T|" + t).encode("utf-8")).hexdigest()[:16]
    MANIFEST[h] = {"text": t, "slow": False}
    return h


def load(k):
    return json.load(open(os.path.join(GEN, "theme_%s.json" % k), encoding="utf-8"))


def audit(k, d):
    out = []
    def check(s, where):
        for pat, why in BANNED:
            if re.search(pat, s, re.I):
                out.append((k, where, why, s))
        n = len(re.findall(r"[A-Za-zÀ-ÿ']+", s))
        if n > MAXWORDS:
            out.append((k, where, "过长 %d 词" % n, s))
    for q in d.get("questions", []):
        check(q, "question")
    for side in ("pour", "contre"):
        for it in d.get(side, []):
            check(it["fr"], side)
            check(it.get("ex", ""), side + ".ex")
    for it in d.get("core", []):
        check(it["fr"], "core")
    return out


def theme_blocks(i, k, zh):
    d = load(k)
    b = [{"kind": "h4", "title": "%s %s · %s" % (CIRC[i], zh, d["fr"])}]
    b.append({"kind": "bullets", "title": "这个主题可能怎么问你",
              "items": [x for x in d["questions"]]})
    for side, label, mark in (("pour", "✓ 好处 / 支持这一边", "✓"),
                              ("contre", "✗ 坏处 / 反对这一边", "✗")):
        rows, aids = [], []
        for it in d[side]:
            rows.append(["<b>%s %s</b><br>%s" % (mark, it["fr"], it["zh"]), it["ex"]])
            aids.append([aid(it["fr"]), aid(it["ex"])])
        b.append({"kind": "table", "title": "%s —— %s" % (zh, label),
                  "columns": ["论点（点一下听）", "具体例子（也能点）"],
                  "rows": rows, "aids": aids})
    b.append({"kind": "cards", "title": "%s —— 四种立场，开头结尾直接用" % zh,
              "cards": [{"fr": c["fr"], "zh": c["zh"], "note": c["note"], "aid": aid(c["fr"])}
                        for c in d["core"]]})
    return b


INTRO_A = ("Tâche 3 最怕的不是不会说，是脑子一片空白。这两章把 10 个高频主题的"
           "<b>好处、坏处、核心立场</b>都提前想好了：抽到题先扫一眼对应主题，"
           "从 6 条好处里挑 2 条、6 条坏处里挑 1 条、再选一句核心立场收尾，一篇论证就成型了。")
INTRO_B = ("<b>这两章的法语是特意压简单的。</b>短句、现在时、日常词，没有虚拟式，"
           "没有 néanmoins 这类书面连接词——因为考场上说得出口、写得对，比句子漂亮重要得多。"
           "评分表看的是<b>结构清楚 + 有具体例子</b>，不是看你会不会用难词。")
HOWTO = ("① 口语：立场（1 句）→ 理由一 + 例子 → 理由二 + 例子 → 让步一句（"
         "« C'est vrai que… mais… »）→ 结论。<br>"
         "② 写作：同样的骨架，只是把口语的停顿换成段落。<br>"
         "③ <b>例子那一列比论点那一列更值钱</b>。所有人都会说「科技让生活更方便」，"
         "只有你会说「我用手机 5 分钟就交完了房租」。<br>"
         "④ 别背满 10 个主题的全部。每个主题记熟 <b>2 条好处 + 1 条坏处 + 1 句立场</b>，"
         "就够应付这个主题下的任何题目。")


def main():
    content = json.load(open(os.path.join(HERE, "data", "content.json"), encoding="utf-8"))
    chapters = content["chapters"]
    if any(c.get("key", "").startswith("t3theme_") for c in chapters):
        raise SystemExit("theme chapters already present")

    problems = []
    for k, zh in THEMES:
        problems += audit(k, load(k))
    print("difficulty violations:", len(problems))
    for p in problems[:25]:
        print("   %-13s %-10s %-16s %s" % (p[0], p[1], p[2], p[3][:70]))

    half = [
        {"key": "t3theme_a", "zh": "Tâche 3 主题论点库（上）：工作 · 教育 · 科技 · 健康 · 环境",
         "fr": "Arguments par thème (1) — travail, éducation, technologie, santé, environnement",
         "intro": "5 个主题，每个主题 6 条好处 + 6 条坏处 + 4 句核心立场，全部配例子和发音。"
                  "语言特意压在简单水平：短句、现在时、日常词。",
         "blocks": ([{"kind": "para", "text": INTRO_A}, {"kind": "para", "text": INTRO_B},
                     {"kind": "tip", "title": "怎么用这两章", "text": HOWTO}] +
                    [x for i, (k, zh) in enumerate(THEMES[:5]) for x in theme_blocks(i, k, zh)])},
        {"key": "t3theme_b", "zh": "Tâche 3 主题论点库（下）：家庭 · 城市生活 · 消费 · 旅游 · 社会",
         "fr": "Arguments par thème (2) — famille, ville, consommation, voyage, société",
         "intro": "另外 5 个主题。用法和上一章一样：挑 2 条好处、1 条坏处、1 句立场，就是一篇完整论证。",
         "blocks": [x for i, (k, zh) in enumerate(THEMES[5:], start=5) for x in theme_blocks(i, k, zh)]},
    ]
    for c in half:
        c["part"] = "VIII"
        c["partzh"] = "Tâche 3 万能理由与句型"
        c["color"] = COLOR

    at = max(i for i, c in enumerate(chapters) if c["part"] == "VIII") + 1
    chapters[at:at] = half
    for i, c in enumerate(chapters):
        c["no"] = i + 1

    json.dump(content, open(os.path.join(HERE, "data", "content.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    json.dump(MANIFEST, open(os.path.join(HERE, "tts_themes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("chapters now:", len(chapters))
    print("new:", [(c["no"], c["zh"][:24]) for c in chapters if c["key"].startswith("t3theme_")])
    print("blocks:", [len(c["blocks"]) for c in half])
    print("clips to synthesize:", len(MANIFEST))


if __name__ == "__main__":
    main()
